from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Coroutine, Dict, Optional, Union
from uuid import uuid4

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer
from structlog import BoundLogger

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.context.req_context import build_req_context, ReqContext
from app.commons.jobs.pool import JobPool
from app.commons.utils import validation
from app.payin.core.cart_payment.model import PaymentIntent
from app.payin.core.cart_payment.processor import (
    CartPaymentInterface,
    CartPaymentProcessor,
    LegacyPaymentInterface,
)
from app.payin.core.cart_payment.types import IntentStatus
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.repository.cart_payment_repo import (
    CartPaymentRepository,
    UpdatePaymentIntentSetInput,
    UpdatePaymentIntentWhereInput,
)
from app.payin.repository.payer_repo import PayerRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository

logger = get_logger("jobs")


class JobInstanceContext:
    """
    A JobInstanceContext is built per each time when a job instance is triggered by scheduler
    """

    app_context: AppContext
    job_pool: JobPool
    job_instance_id: str
    job_name: str
    log: BoundLogger

    def __init__(self, app_context: AppContext, job_pool: JobPool, job_name: str):
        self.app_context = app_context
        self.job_pool = job_pool
        self.job_name = job_name
        self.job_instance_id = str(uuid4())
        self.log = app_context.log.bind(
            job_instance_id=self.job_instance_id, job_name=self.job_name
        )

    def build_req_context(self) -> ReqContext:
        """
        Build a request context with logger bind with job_name and job_instance_id
        :return:
        """
        return build_req_context(
            self.app_context,
            job_name=self.job_name,
            job_instance_id=self.job_instance_id,
        )


class Job(ABC):
    """
    Encapsulate a defined Job.
    An instance of a Job is callable that can be invoked by scheduler.
    """

    app_context: AppContext
    job_pool: JobPool
    _statsd_client: DoorStatsProxyMultiServer

    def __init__(
        self,
        *,
        app_context: AppContext,
        job_pool: JobPool,
        statsd_client: DoorStatsProxyMultiServer,
    ):
        self.app_context = app_context
        self.job_pool = job_pool
        self._statsd_client = statsd_client

    @property
    @abstractmethod
    def job_name(self) -> str:
        pass

    @abstractmethod
    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        """
        Sub class should implement trigger logic which will be invoked at each time this job being triggered by scheduler
        :param job_instance_cxt:
        :return:
        """
        raise NotImplementedError("sub class must implement this method!")

    def _stats_tag(self) -> Dict[str, str]:
        return {"job": self.job_name}

    async def stats_incr(
        self, *, metric_name: str, tags: Optional[Dict[str, str]] = None
    ):
        all_tags = self._stats_tag()
        if tags:
            all_tags.update(tags)

        self._statsd_client.incr(metric_name, tags=all_tags)

    async def stats_gauge(
        self,
        *,
        metric_name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None,
    ):
        all_tags = self._stats_tag()
        if tags:
            all_tags.update(tags)
        self._statsd_client.gauge(metric_name, value, tags=all_tags)

    async def run(self):
        """
        Actually trigger and run a new instance defined by this job.
        - Each run will assign a unique job_instance_id for the newly created job instance
        - When add a job to scheduler, need to do
            ```
            scheduler.add_job(somejob.run, ...)
            ```
          to provider scheduler a "coroutine function" to invoke
        :return:
        """
        jon_instance_cxt: JobInstanceContext = JobInstanceContext(
            app_context=self.app_context, job_pool=self.job_pool, job_name=self.job_name
        )
        await self.stats_incr(metric_name="job-trigger-start")
        jon_instance_cxt.log.info("Triggering job instance")
        await self._trigger(jon_instance_cxt)
        await self.stats_incr(metric_name="job-trigger-finish")
        jon_instance_cxt.log.info("Triggered job instance")


async def job_callback(res, err, ctx):
    if err:
        logger.error(
            "Exception running job", exc_info=err[0]
        )  # err = (exec, traceback)
    else:
        logger.debug("Job successfully completed")


class CaptureUncapturedPaymentIntents(Job):
    """
    Captures all uncaptured payment intents
    """

    _problematic_capture_delay: timedelta

    def __init__(
        self,
        *,
        app_context: AppContext,
        job_pool: JobPool,
        problematic_capture_delay: timedelta,
        statsd_client: DoorStatsProxyMultiServer,
    ):
        super().__init__(
            app_context=app_context, job_pool=job_pool, statsd_client=statsd_client
        )
        self._problematic_capture_delay = problematic_capture_delay

    @property
    def job_name(self) -> str:
        return "CaptureUncapturedPaymentIntents"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        cart_payment_repo = CartPaymentRepository(context=job_instance_cxt.app_context)
        payer_repo = PayerRepository(context=job_instance_cxt.app_context)
        payment_method_repo = PaymentMethodRepository(
            context=job_instance_cxt.app_context
        )

        utcnow = datetime.now(timezone.utc)
        start_time = utcnow

        uncaptured_payment_intents = cart_payment_repo.find_payment_intents_that_require_capture(
            capturable_before=utcnow,
            earliest_capture_after=utcnow - self._problematic_capture_delay,
        )

        processed_payment_intent_count: int = 0
        async for payment_intent in uncaptured_payment_intents:
            processed_payment_intent_count += 1
            await job_instance_cxt.job_pool.spawn(
                self._capture_payment(
                    payment_intent=payment_intent,
                    cart_payment_repo=cart_payment_repo,
                    payer_repo=payer_repo,
                    payment_method_repo=payment_method_repo,
                    job_instance_cxt=job_instance_cxt,
                ),
                cb=job_callback,
            )

        # last task to emit actual finished time and count after everything in this job instance is done
        await job_instance_cxt.job_pool.spawn(
            self._stats_job(
                job_instance_cxt=job_instance_cxt,
                start_time=start_time,
                processed_payment_intent_count=processed_payment_intent_count,
            )
        )

    async def _stats_job(
        self,
        *,
        job_instance_cxt: JobInstanceContext,
        start_time: datetime,
        processed_payment_intent_count: int,
    ):
        now = datetime.now(timezone.utc)
        duration_sec = (now - start_time).seconds

        await self.stats_incr(metric_name=f"capture-payment.completed")

        await self.stats_gauge(
            metric_name=f"capture-payment.duration", value=duration_sec
        )
        await self.stats_gauge(
            metric_name=f"capture-payment.processed-payment-intent-count",
            value=processed_payment_intent_count,
        )
        job_instance_cxt.log.info(
            "payment_intent count summary",
            processed_payment_intent_count=processed_payment_intent_count,
            started=start_time,
            finished=now,
            duration=duration_sec,
        )

    async def _capture_payment(
        self,
        payment_intent: PaymentIntent,
        cart_payment_repo: CartPaymentRepository,
        payer_repo: PayerRepository,
        payment_method_repo: PaymentMethodRepository,
        job_instance_cxt: JobInstanceContext,
    ):
        """
        Build request scoped processor and  attach req_id to each processor call
        :param payment_intent:
        :param cart_payment_repo:
        :param payer_repo:
        :param payment_method_repo:
        :param job_instance_cxt:
        :return:
        """
        cart_payment_processor: CartPaymentProcessor = self._build_request_scoped_cart_payment_processor(
            cart_payment_repo=cart_payment_repo,
            payer_repo=payer_repo,
            payment_method_repo=payment_method_repo,
            job_instance_cxt=job_instance_cxt,
        )
        await cart_payment_processor.capture_payment(payment_intent)

    def _build_request_scoped_cart_payment_processor(
        self,
        cart_payment_repo: CartPaymentRepository,
        payer_repo: PayerRepository,
        payment_method_repo: PaymentMethodRepository,
        job_instance_cxt: JobInstanceContext,
    ) -> CartPaymentProcessor:
        req_context = job_instance_cxt.build_req_context()

        payer_client = PayerClient(
            app_ctxt=job_instance_cxt.app_context,
            log=req_context.log,
            payer_repo=payer_repo,
            stripe_async_client=req_context.stripe_async_client,
        )
        payment_method_client = PaymentMethodClient(
            payment_method_repo=payment_method_repo,
            log=req_context.log,
            app_ctxt=job_instance_cxt.app_context,
            stripe_async_client=req_context.stripe_async_client,
        )
        cart_payment_interface = CartPaymentInterface(
            app_context=job_instance_cxt.app_context,
            req_context=req_context,
            payment_repo=cart_payment_repo,
            payer_client=payer_client,
            payment_method_client=payment_method_client,
            stripe_async_client=req_context.stripe_async_client,
        )
        legacy_payment_interface = LegacyPaymentInterface(
            app_context=job_instance_cxt.app_context,
            req_context=req_context,
            payment_repo=cart_payment_repo,
            stripe_async_client=req_context.stripe_async_client,
        )

        return CartPaymentProcessor(
            log=req_context.log,
            cart_payment_interface=cart_payment_interface,
            legacy_payment_interface=legacy_payment_interface,
        )


class ResolveCapturingPaymentIntents(Job):
    """
    Pick up payment intents that stuck at [capturing] state for a while and reset their states to
    next actionable states.

    Depending on how long the intent has been in [capturing] state:
    1. If payment_intent.capture_after is earlier than "problematic_capture_delay" than we consider this capture
        is permanently failed due to errors during capturing. Set state to [capture_failed]
    2. If payment_intent.capture_after is within "problematic_capture_delay" than we consider this capture
        can still be retried and set its status to [requires_capture]
    """

    statsd_client: DoorStatsProxyMultiServer
    _problematic_capture_delay: timedelta

    def __init__(
        self,
        *,
        app_context: AppContext,
        job_pool: JobPool,
        problematic_capture_delay: timedelta,
        statsd_client: DoorStatsProxyMultiServer,
    ):
        super().__init__(
            app_context=app_context, job_pool=job_pool, statsd_client=statsd_client
        )
        self._problematic_capture_delay = problematic_capture_delay

    @property
    def job_name(self) -> str:
        return "ResolveCapturingPaymentIntents"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        cart_payment_repo = CartPaymentRepository(job_instance_cxt.app_context)
        utcnow = datetime.now(timezone.utc)

        # Look for payment intents that haven't been updated in an hour and still in capturing
        # This should be a good indication that the capturing process died

        cutoff = utcnow - timedelta(hours=1)

        # when we "scan" through past created payment intent, we double the oldest_capture_intents_age
        # just in case there were intents which set to capture at boundary of this threshold cannot be picked up.
        earliest_capture_after = utcnow - self._problematic_capture_delay * 2

        payment_intents = await cart_payment_repo.find_payment_intents_in_capturing(
            earliest_capture_after=earliest_capture_after
        )

        to_requires_capture_count = 0
        to_capture_failed_count = 0
        skipped_count = 0
        for payment_intent in payment_intents:

            # if this payment intent was updated to capturing within cutoff
            # we consider it is very possible this intent is BEING captured, therefore skip it.
            if payment_intent.updated_at >= cutoff:
                skipped_count += 1
                continue

            new_status: IntentStatus
            task: Coroutine

            capture_after = validation.not_none(payment_intent.capture_after)
            capture_after = (
                capture_after
                if capture_after.tzinfo
                else capture_after.replace(tzinfo=timezone.utc)
            )

            if capture_after >= utcnow - self._problematic_capture_delay:
                new_status = IntentStatus.REQUIRES_CAPTURE
                to_requires_capture_count += 1
            else:
                new_status = IntentStatus.CAPTURE_FAILED
                to_capture_failed_count += 1

            update_payment_intent_status_where_input = UpdatePaymentIntentWhereInput(
                id=payment_intent.id, previous_status=payment_intent.status
            )
            update_payment_intent_status_set_input = UpdatePaymentIntentSetInput(
                status=new_status, updated_at=datetime.now(timezone.utc)
            )
            task = cart_payment_repo.update_payment_intent(
                update_payment_intent_status_where_input=update_payment_intent_status_where_input,
                update_payment_intent_status_set_input=update_payment_intent_status_set_input,
            )

            job_instance_cxt.log.info(
                "Resolving payment_intent status",
                payment_intent=payment_intent.summary,
                payment_intent_new_status=new_status,
            )

            await job_instance_cxt.job_pool.spawn(task)

        job_instance_cxt.log.info(
            "payment_intent resolving status summary",
            to_requires_capture_count=to_requires_capture_count,
            to_capture_failed_count=to_capture_failed_count,
            skipped_count=skipped_count,
        )
        await self.stats_gauge(
            metric_name=f"resolve-payment-intent-status-to.{IntentStatus.CAPTURE_FAILED.value}.count",
            value=to_capture_failed_count,
        )
        await self.stats_gauge(
            metric_name=f"resolve-payment-intent-status-to.{IntentStatus.REQUIRES_CAPTURE.value}.count",
            value=to_requires_capture_count,
        )


class EmitProblematicCaptureCount(Job):
    """
    Emits the number of problematic captures to statsd
    """

    statsd_client: DoorStatsProxyMultiServer
    problematic_threshold: timedelta

    def __init__(
        self,
        app_context: AppContext,
        job_pool: JobPool,
        statsd_client: DoorStatsProxyMultiServer,
        problematic_threshold: timedelta,
    ):
        super().__init__(
            app_context=app_context, job_pool=job_pool, statsd_client=statsd_client
        )
        self.statsd_client = statsd_client
        self.problematic_threshold = problematic_threshold

    @property
    def job_name(self) -> str:
        return "EmitProblematicCaptureCount"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        cart_payment_repo = CartPaymentRepository(self.app_context)
        count = await cart_payment_repo.count_payment_intents_in_problematic_states(
            problematic_threshold=self.problematic_threshold
        )
        job_instance_cxt.log.info(
            "emit problematic payment intents summary",
            problematic_count=count,
            problematic_threshold=self.problematic_threshold,
        )
        await self.stats_gauge(
            metric_name="payment-intent-problematic-state.count", value=count
        )
