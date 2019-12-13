import inspect
from typing import Optional, List
from uuid import uuid4

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payout.core.transfer.processors.weekly_create_transfer import (
    WeeklyCreateTransferRequest,
    WeeklyCreateTransfer,
)
from app.payout.core.transfer.tasks.base_task import BaseTask, normalize_task_arguments
from app.payout.models import PayoutDay, PayoutCountry, PayoutTask
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository


class WeeklyCreateTransferTask(BaseTask):
    def __init__(
        self,
        payout_day: PayoutDay,
        payout_countries: List[PayoutCountry],
        end_time: str,
        unpaid_txn_start_time: str,
        whitelist_payment_account_ids: List[int],
        exclude_recently_updated_accounts: Optional[bool] = False,
    ):
        self.topic_name = "payment_payout"
        self.task_type = PayoutTask.WEEKLY_CREATE_TRANSFER
        auto_retry_for: List[Exception] = []
        max_retries: int = 0
        fn_args: list = []
        super().__init__(
            self.topic_name,
            self.task_type,
            auto_retry_for,
            max_retries,
            fn_args,
            normalize_task_arguments(inspect.currentframe()),
        )

    @staticmethod
    async def run(app_context: AppContext, data: dict):
        transfer_repo = TransferRepository(database=app_context.payout_maindb)
        transaction_repo = TransactionRepository(database=app_context.payout_bankdb)
        payment_account_repo = PaymentAccountRepository(
            database=app_context.payout_maindb
        )
        payment_account_edit_history_repo = PaymentAccountEditHistoryRepository(
            database=app_context.payout_bankdb
        )
        stripe_transfer_repo = StripeTransferRepository(
            database=app_context.payout_maindb
        )
        managed_account_transfer_repo = ManagedAccountTransferRepository(
            database=app_context.payout_maindb
        )

        # convert to weekly create transfer
        req_context = build_req_context(
            app_context, task_name="WeeklyCreateTransferTask", task_id=str(uuid4())
        )
        weekly_create_transfer_request_dict = {}
        if "fn_kwargs" in data:
            data_kwargs = data["fn_kwargs"]
            for k, v in data_kwargs.items():
                weekly_create_transfer_request_dict[k] = v

        weekly_create_transfer_op_dict = {
            "transfer_repo": transfer_repo,
            "payment_account_repo": payment_account_repo,
            "stripe_transfer_repo": stripe_transfer_repo,
            "managed_account_transfer_repo": managed_account_transfer_repo,
            "transaction_repo": transaction_repo,
            "payment_account_edit_history_repo": payment_account_edit_history_repo,
            "stripe": req_context.stripe_async_client,
            "payment_lock_manager": app_context.redis_lock_manager,
            "kafka_producer": app_context.kafka_producer,
            "logger": req_context.log,
            "request": WeeklyCreateTransferRequest(
                **weekly_create_transfer_request_dict
            ),
        }
        weekly_create_transfer_op = WeeklyCreateTransfer(
            **weekly_create_transfer_op_dict
        )
        await weekly_create_transfer_op.execute()
