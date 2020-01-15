from datetime import datetime, timezone

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.jobs.pool import JobPool
from app.jobs.model import JobInstanceContext, Job
from app.payin.core.cart_payment.processor import (
    CartPaymentInterface,
    LegacyPaymentInterface,
)
from app.payin.core.feature_flags import enable_delete_payer_processing
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.types import DeletePayerRequestStatus
from app.payin.core.payer.v0.processor import DeletePayerProcessor
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import (
    PayerRepository,
    FindDeletePayerRequestByStatusInput,
    DeletePayerRequestDbEntity,
)
from app.payin.repository.payment_method_repo import PaymentMethodRepository

logger = get_logger("delete_payer_job")


async def job_callback(res, err, ctx):
    if err:
        logger.error(
            "[job_callback] Exception running job", exc_info=err[0]
        )  # err = (exec, traceback)
    else:
        logger.info("[job_callback] Job successfully completed")


class DeletePayer(Job):
    def __init__(
        self,
        *,
        app_context: AppContext,
        job_pool: JobPool,
        statsd_client: DoorStatsProxyMultiServer,
    ):
        super().__init__(
            app_context=app_context, job_pool=job_pool, statsd_client=statsd_client
        )

    @property
    def job_name(self) -> str:
        return "DeletePayer"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        if not enable_delete_payer_processing():
            return

        payer_repo = PayerRepository(context=job_instance_cxt.app_context)
        payment_method_repo = PaymentMethodRepository(
            context=job_instance_cxt.app_context
        )
        cart_payment_repo = CartPaymentRepository(context=job_instance_cxt.app_context)

        delete_payer_requests_in_progress = await payer_repo.find_delete_payer_requests_by_status(
            find_delete_payer_request_by_status_input=FindDeletePayerRequestByStatusInput(
                status=DeletePayerRequestStatus.IN_PROGRESS
            )
        )

        utcnow = datetime.now(timezone.utc)
        start_time = utcnow
        processed_delete_payer_count: int = 0
        for delete_payer_request in delete_payer_requests_in_progress:
            processed_delete_payer_count += 1
            await job_instance_cxt.job_pool.spawn(
                self._delete_payer(
                    max_retries=5,
                    delete_payer_request=delete_payer_request,
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
                processed_delete_payer_count=processed_delete_payer_count,
            )
        )

    async def _stats_job(
        self,
        *,
        job_instance_cxt: JobInstanceContext,
        start_time: datetime,
        processed_delete_payer_count: int,
    ):
        now = datetime.now(timezone.utc)
        duration_sec = (now - start_time).seconds

        await self.stats_incr(metric_name=f"delete-payer.completed")

        await self.stats_gauge(metric_name=f"delete-payer.duration", value=duration_sec)

        await self.stats_gauge(
            metric_name=f"delete-payer.processed-delete-payer-count",
            value=processed_delete_payer_count,
        )
        job_instance_cxt.log.info(
            "[_stats_job] delete payer count summary",
            processed_delete_payer_count=processed_delete_payer_count,
            started=start_time,
            finished=now,
            duration=duration_sec,
        )

    async def _delete_payer(
        self,
        max_retries: int,
        delete_payer_request: DeletePayerRequestDbEntity,
        cart_payment_repo: CartPaymentRepository,
        payer_repo: PayerRepository,
        payment_method_repo: PaymentMethodRepository,
        job_instance_cxt: JobInstanceContext,
    ):
        """
        Build request scoped processor and  attach req_id to each processor call
        :param max_retries:
        :param delete_payer_request:
        :param cart_payment_repo:
        :param payer_repo:
        :param payment_method_repo:
        :param job_instance_cxt:
        :return:
        """
        delete_payer_processor: DeletePayerProcessor = self._build_request_scoped_delete_payer_processor(
            max_retries=max_retries,
            cart_payment_repo=cart_payment_repo,
            payer_repo=payer_repo,
            payment_method_repo=payment_method_repo,
            job_instance_cxt=job_instance_cxt,
        )
        await delete_payer_processor.delete_payer(delete_payer_request)

    def _build_request_scoped_delete_payer_processor(
        self,
        max_retries: int,
        cart_payment_repo: CartPaymentRepository,
        payer_repo: PayerRepository,
        payment_method_repo: PaymentMethodRepository,
        job_instance_cxt: JobInstanceContext,
    ) -> DeletePayerProcessor:
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

        return DeletePayerProcessor(
            max_retries=max_retries,
            log=req_context.log,
            app_context=job_instance_cxt.app_context,
            payer_client=payer_client,
            payment_method_client=payment_method_client,
            cart_payment_interface=cart_payment_interface,
            legacy_payment_interface=legacy_payment_interface,
        )
