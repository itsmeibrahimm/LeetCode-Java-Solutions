from abc import ABC, abstractmethod
from datetime import datetime, timedelta, tzinfo
from typing import List
from uuid import uuid4

import pytz
from structlog import BoundLogger

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.context.req_context import ReqContext, build_req_context
from app.commons.jobs.pool import JobPool
from app.payout.constants import ENABLE_QUEUEING_MECHANISM_FOR_PAYOUT
from app.payout.core.transfer.processors.update_transfer_by_stripe_transfer_status import (
    UpdateTransferByStripeTransferStatus,
    UpdateTransferByStripeTransferStatusRequest,
)
from app.payout.core.transfer.processors.weekly_create_transfer import (
    WeeklyCreateTransfer,
    WeeklyCreateTransferRequest,
)
from app.payout.core.transfer.tasks.weekly_create_transfer_task import (
    WeeklyCreateTransferTask,
)
from app.payout.core.transfer.utils import get_last_week
from app.payout.models import PayoutDay, PayoutCountry
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.instant_payout.models import (
    CheckSMABalanceRequest,
    SMATransferRequest,
    SubmitInstantPayoutRequest,
)
from app.payout.core.instant_payout.processors.pgp.check_sma_balance import (
    CheckSMABalance,
)
from app.payout.core.instant_payout.processors.pgp.submit_instant_payout import (
    SubmitInstantPayout,
)
from app.payout.core.instant_payout.processors.pgp.submit_sma_transfer import (
    SubmitSMATransfer,
)
from app.payout.core.instant_payout.utils import create_idempotency_key
from app.payout.repository.bankdb.model.payout import Payout
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.commons.runtime import runtime

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


class MonitorTransfersWithIncorrectStatus(Job):
    @property
    def job_name(self) -> str:
        return "MonitorTransfersWithIncorrectStatus"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        if runtime.get_bool(
            "payout/feature-flags/enable_payment_service_monitor_transfer_with_incorrect_status.bool",
            False,
        ):
            # Create a window of the last 7 days
            start = self._start_of_the_week(date=datetime.utcnow()) - timedelta(weeks=1)
            stripe_transfer_repo = StripeTransferRepository(
                database=job_instance_cxt.app_context.payout_maindb
            )
            transfer_repo = TransferRepository(
                database=job_instance_cxt.app_context.payout_maindb
            )
            transfer_ids = await transfer_repo.get_transfers_by_submitted_at_and_method(
                start_time=start
            )

            job_instance_cxt.log.info(
                "[monitor_transfers_with_incorrect_status] Starting execution",
                start_time=start,
                transfers_total_number=len(transfer_ids),
            )
            req_context = job_instance_cxt.build_req_context()

            for transfer_id in transfer_ids:
                update_transfer_req = UpdateTransferByStripeTransferStatusRequest(
                    transfer_id=transfer_id
                )
                update_transfer_by_stripe_transfer_status_op = UpdateTransferByStripeTransferStatus(
                    transfer_repo=transfer_repo,
                    stripe_transfer_repo=stripe_transfer_repo,
                    stripe=req_context.stripe_async_client,
                    logger=logger,
                    request=update_transfer_req,
                )
                await job_instance_cxt.job_pool.spawn(
                    update_transfer_by_stripe_transfer_status_op.execute(),
                    cb=job_callback,
                )

    def _start_of_the_week(self, date: datetime) -> datetime:
        return date - timedelta(days=date.weekday())


class RetryInstantPayoutInNew(Job):
    @property
    def job_name(self) -> str:
        return "RetryInstantPayoutInNew"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        """RetryInstantPayoutInNew trigger.

        Get all instant payouts in new status from [current_time - 3 hours, current_time - 0.5 hour], and retry. The
        cron is controlled through feature flag.
        """
        if not runtime.get_bool(
            "payout/feature-flags/enable_payment_service_instant_pay_cron_job.bool",
            False,
        ):
            return

        req_context = job_instance_cxt.build_req_context()
        stripe_async_client = req_context.stripe_async_client
        log = req_context.log
        payout_repo = PayoutRepository(job_instance_cxt.app_context.payout_bankdb)
        payout_account_repo = PaymentAccountRepository(
            job_instance_cxt.app_context.payout_maindb
        )
        payout_card_repo = PayoutCardRepository(
            job_instance_cxt.app_context.payout_bankdb
        )
        stripe_managed_account_transfer_repo = StripeManagedAccountTransferRepository(
            job_instance_cxt.app_context.payout_bankdb
        )
        stripe_payout_request_repo = StripePayoutRequestRepository(
            job_instance_cxt.app_context.payout_bankdb
        )
        transaction_repo = TransactionRepository(
            job_instance_cxt.app_context.payout_bankdb
        )

        log.info("[Payment Service RetryInstantPayoutInNew Cron]")

        # Get all payouts in new status more than 30 minutes
        current_time = datetime.utcnow().replace(tzinfo=pytz.utc)
        end_time = current_time - timedelta(minutes=30)
        payouts_in_new = await payout_repo.list_payout_in_new_status(end_time=end_time)

        for payout in payouts_in_new:
            # For payouts more than 3 hours, just log as warning
            if current_time - payout.created_at.replace(tzinfo=pytz.utc) > timedelta(
                hours=3
            ):
                log.warn(
                    "[Payment Service RetryInstantPayoutInNew Cron]: found payout in new "
                    "more than 3 hours, need manual operation",
                    payout_id=payout.id,
                    payout_account_id=payout.payment_account_id,
                )
                continue
            await job_instance_cxt.job_pool.spawn(
                retry_instant_payout(
                    payout=payout,
                    payout_repo=payout_repo,
                    payout_account_repo=payout_account_repo,
                    payout_card_repo=payout_card_repo,
                    stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
                    stripe_payout_request_repo=stripe_payout_request_repo,
                    transaction_repo=transaction_repo,
                    stripe_async_client=stripe_async_client,
                    log=log,
                ),
                cb=job_callback,
            )


async def retry_instant_payout(
    payout: Payout,
    payout_repo: PayoutRepository,
    payout_account_repo: PaymentAccountRepository,
    payout_card_repo: PayoutCardRepository,
    stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
    stripe_payout_request_repo: StripePayoutRequestRepository,
    transaction_repo: TransactionRepository,
    stripe_async_client: StripeAsyncClient,
    log: BoundLogger,
):
    """Retry Instant Payout in New status.

    This function execute/retry the main steps of submitting an instant payout,
        - check stripe connected account balance
        - submit connected account transfer if needed
        - submit instant payout

    The retry of instant payout highly rely on stripe's idempotency key, so the payout object passed in **must** within
    24 hours limit, or it will cause double pay.

    :param payout: payout record
    :param payout_repo: payout repository
    :param payout_account_repo: payout account repository
    :param payout_card_repo: payout card repository
    :param stripe_managed_account_transfer_repo: stripe managed account transfer repository
    :param stripe_payout_request_repo: stripe payout request repo
    :param transaction_repo: transaction repository
    :param stripe_async_client stripe async client
    :param log: log
    :return: None, will print out log
    """

    # get payout account
    payout_account = await payout_account_repo.get_payment_account_by_id(
        payment_account_id=payout.payment_account_id
    )
    if payout_account is None or not payout_account.account_id:
        log.warn("Failed to get payout account")
        return

    # get stripe_managed_account
    stripe_managed_account = await payout_account_repo.get_stripe_managed_account_by_id(
        stripe_managed_account_id=payout_account.account_id
    )
    if stripe_managed_account is None:
        log.warn("Failed to get stripe managed account")
        return

    # get payout_card
    payout_card = await payout_card_repo.get_payout_card_by_id(
        payout_card_id=payout.payout_method_id
    )
    if payout_card is None:
        log.warn("Failed to get payout card")
        return

    try:
        # 1. Check balance
        check_sma_balance_request = CheckSMABalanceRequest(
            stripe_managed_account_id=stripe_managed_account.stripe_id,
            country=stripe_managed_account.country_shortname,
        )
        check_sma_balance_op = CheckSMABalance(
            request=check_sma_balance_request,
            stripe_client=stripe_async_client,
            logger=log,
        )
        sma_balance = await check_sma_balance_op.execute()

        # 2. Submit SMA Transfer if needed
        if sma_balance.balance < payout.amount:
            amount_needed = payout.amount - sma_balance.balance
            sma_transfer_request = SMATransferRequest(
                payout_id=payout.id,
                transaction_ids=payout.transaction_ids,
                amount=amount_needed,
                currency=payout.currency,
                destination=stripe_managed_account.stripe_id,
                country=stripe_managed_account.country_shortname.upper(),
                idempotency_key=create_idempotency_key(prefix=None),
            )
            submit_sma_transfer_op = SubmitSMATransfer(
                request=sma_transfer_request,
                stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
                stripe_client=stripe_async_client,
                payout_repo=payout_repo,
                transaction_repo=transaction_repo,
                logger=log,
            )
            await submit_sma_transfer_op.execute()

        # 3. Submit Instant Payout
        submit_instant_payout_request = SubmitInstantPayoutRequest(
            payout_id=payout.id,
            transaction_ids=payout.transaction_ids,
            country=stripe_managed_account.country_shortname.upper(),
            stripe_account_id=stripe_managed_account.stripe_id,
            amount=payout.amount,
            currency=payout.currency.lower(),
            payout_method_id=payout.payout_method_id,
            destination=payout_card.stripe_card_id,
            # To make request idempotent, must use idempotency_key of current payout record
            idempotency_key=payout.idempotency_key,
        )

        submit_instant_payout_op = SubmitInstantPayout(
            request=submit_instant_payout_request,
            stripe_client=stripe_async_client,
            stripe_payout_request_repo=stripe_payout_request_repo,
            payout_repo=payout_repo,
            transaction_repo=transaction_repo,
            logger=log,
        )
        submit_instant_payout_response = await submit_instant_payout_op.execute()

        log.info(
            "[Payment Service RetryInstantPayoutInNew]: Succeed to retry Instant Payout",
            response=submit_instant_payout_response.dict(),
        )

    except Exception as e:
        log.exception(
            "[Payment Service RetryInstantPayoutInNew]: Failed to retry Instant Payout",
            payout_id=payout.id,
            payout_account_id=payout.payment_account_id,
            error=str(e),
        )


class WeeklyCreateTransferJob(Job):
    payout_country_timezone: tzinfo
    payout_day: PayoutDay
    payout_countries: List[PayoutCountry]

    def __init__(
        self,
        *,
        app_context: AppContext,
        job_pool: JobPool,
        payout_countries: List[PayoutCountry],
        payout_country_timezone: tzinfo,
        payout_day: PayoutDay
    ):
        self.app_context = app_context
        self.job_pool = job_pool
        self.payout_countries = payout_countries
        self.payout_country_timezone = payout_country_timezone
        self.payout_day = payout_day
        super().__init__(app_context=app_context, job_pool=job_pool)

    @property
    def job_name(self) -> str:
        return "WeeklyCreateTransfer"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        weekly_create_transfers_dict_list = runtime.get_json(
            "payout/feature-flags/enable_payment_service_weekly_create_transfers_list.json",
            [],
        )
        weekly_create_transfers_list: List[int] = []
        for weekly_create_transfer_dict_obj in weekly_create_transfers_dict_list:
            for key in weekly_create_transfer_dict_obj.keys():
                weekly_create_transfers_list.append(int(key))
        if weekly_create_transfers_list:
            transfer_repo = TransferRepository(
                database=job_instance_cxt.app_context.payout_maindb
            )
            transaction_repo = TransactionRepository(
                database=job_instance_cxt.app_context.payout_bankdb
            )
            payment_account_repo = PaymentAccountRepository(
                database=job_instance_cxt.app_context.payout_maindb
            )
            payment_account_edit_history_repo = PaymentAccountEditHistoryRepository(
                database=job_instance_cxt.app_context.payout_bankdb
            )
            stripe_transfer_repo = StripeTransferRepository(
                database=job_instance_cxt.app_context.payout_maindb
            )
            managed_account_transfer_repo = ManagedAccountTransferRepository(
                database=job_instance_cxt.app_context.payout_maindb
            )
            req_context = job_instance_cxt.build_req_context()

            start_time, end_time = get_last_week(
                timezone_info=self.payout_country_timezone, inclusive_end=True
            )

            if runtime.get_bool(ENABLE_QUEUEING_MECHANISM_FOR_PAYOUT, False):
                # put weekly_create_transfer into queue
                weekly_create_transfer_task = WeeklyCreateTransferTask(
                    payout_day=self.payout_day,
                    payout_countries=self.payout_countries,
                    end_time=end_time,
                    unpaid_txn_start_time=start_time,
                    exclude_recently_updated_accounts=False,
                    whitelist_payment_account_ids=weekly_create_transfers_list,
                )
                await job_instance_cxt.job_pool.spawn(
                    weekly_create_transfer_task.send(
                        kafka_producer=job_instance_cxt.app_context.kafka_producer
                    ),
                    cb=job_callback,
                )
            else:
                weekly_create_transfer_req = WeeklyCreateTransferRequest(
                    payout_day=self.payout_day,
                    payout_countries=self.payout_countries,
                    end_time=end_time,
                    unpaid_txn_start_time=start_time,
                    exclude_recently_updated_accounts=False,
                    whitelist_payment_account_ids=weekly_create_transfers_list,
                )
                weekly_create_transfer_op = WeeklyCreateTransfer(
                    transfer_repo=transfer_repo,
                    transaction_repo=transaction_repo,
                    payment_account_repo=payment_account_repo,
                    payment_account_edit_history_repo=payment_account_edit_history_repo,
                    stripe_transfer_repo=stripe_transfer_repo,
                    managed_account_transfer_repo=managed_account_transfer_repo,
                    stripe=req_context.stripe_async_client,
                    payment_lock_manager=job_instance_cxt.app_context.redis_lock_manager,
                    kafka_producer=job_instance_cxt.app_context.kafka_producer,
                    logger=logger,
                    request=weekly_create_transfer_req,
                )
                await job_instance_cxt.job_pool.spawn(
                    weekly_create_transfer_op.execute(), cb=job_callback
                )