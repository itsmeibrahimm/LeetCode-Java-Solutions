from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer
from structlog import BoundLogger

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.context.req_context import ReqContext, build_req_context
from app.commons.jobs.pool import JobPool
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
    UpdatePaymentIntentStatusWhereInput,
    UpdatePaymentIntentStatusSetInput,
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

    def __init__(self, *, app_context: AppContext, job_pool: JobPool):
        self.app_context = app_context
        self.job_pool = job_pool

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
        jon_instance_cxt.log.info("Triggering job instance")
        await self._trigger(jon_instance_cxt)
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

    @property
    def job_name(self) -> str:
        return "CaptureUncapturedPaymentIntents"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        cart_payment_repo = CartPaymentRepository(context=job_instance_cxt.app_context)
        payer_repo = PayerRepository(context=job_instance_cxt.app_context)
        payment_method_repo = PaymentMethodRepository(
            context=job_instance_cxt.app_context
        )

        uncaptured_payment_intents = cart_payment_repo.find_payment_intents_that_require_capture_before_cutoff(
            datetime.utcnow()
        )

        payment_intent_count: int = 0
        payment_intent_skipped_count: int = 0
        expire_cutoff_days = 7
        async for payment_intent in uncaptured_payment_intents:
            payment_intent_count += 1
            if payment_intent.created_at + timedelta(
                days=expire_cutoff_days
            ) < datetime.now(payment_intent.created_at.tzinfo):
                # TODO: [PAYIN-120] this is a dirty fix to avoid spamming stripe by capture expired intents.
                job_instance_cxt.log.warn(
                    f"skipping payment_intent created more than {expire_cutoff_days} days",
                    payment_intent=payment_intent.summary,
                )
                payment_intent_skipped_count += 1
            else:
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
        job_instance_cxt.log.info(
            "payment_intent count summary",
            payment_intent_count=payment_intent_count,
            payment_intent_skipped_count=payment_intent_skipped_count,
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
    Payment intents that are in capturing and haven't been updated in a while likely died.
    The capturing process idempotently handles captures, so it should be fine just to re-set
    the state of these payment intents to requires_capture and let the regular cron just try
    to re-capture.
    """

    @property
    def job_name(self) -> str:
        return "ResolveCapturingPaymentIntents"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        cart_payment_repo = CartPaymentRepository(job_instance_cxt.app_context)

        # Look for payment intents that haven't been updated in an hour and still in capturing
        # This should be a good indication that the capturing process died
        cutoff = datetime.utcnow() - timedelta(hours=1)
        payment_intents = await cart_payment_repo.find_payment_intents_in_capturing(
            cutoff
        )

        count = 0
        for payment_intent in payment_intents:
            count += 1
            new_status = IntentStatus.REQUIRES_CAPTURE.value
            job_instance_cxt.log.info(
                "flip capturing intent to requires_capture",
                job="resolve_capturing_payment_intents",
                payment_intent=payment_intent.summary,
                payment_intent_new_status=new_status,
            )
            update_payment_intent_status_where_input = UpdatePaymentIntentStatusWhereInput(
                id=payment_intent.id, previous_status=payment_intent.status
            )
            update_payment_intent_status_set_input = UpdatePaymentIntentStatusSetInput(
                status=new_status, updated_at=datetime.now(timezone.utc)
            )
            await job_instance_cxt.job_pool.spawn(
                cart_payment_repo.update_payment_intent_status(
                    update_payment_intent_status_where_input=update_payment_intent_status_where_input,
                    update_payment_intent_status_set_input=update_payment_intent_status_set_input,
                )
            )
        job_instance_cxt.log.info("payment_intent summary", payment_intent_count=count)


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
        super().__init__(app_context=app_context, job_pool=job_pool)
        self.statsd_client = statsd_client
        self.problematic_threshold = problematic_threshold

    @property
    def job_name(self) -> str:
        return "EmitProblematicCaptureCount"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        cart_payment_repo = CartPaymentRepository(self.app_context)
        count = await cart_payment_repo.count_payment_intents_that_require_capture(
            problematic_threshold=self.problematic_threshold
        )
        self.statsd_client.gauge("capture.problematic_count", count)
