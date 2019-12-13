import inspect
from typing import Optional, List
from uuid import uuid4

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferRequest,
    SubmitTransfer,
)
from app.payout.core.transfer.tasks.base_task import BaseTask, normalize_task_arguments
from app.payout.models import PayoutTask, TransferMethodType
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


class SubmitTransferTask(BaseTask):
    def __init__(
        self,
        transfer_id: int,
        submitted_by: Optional[int],
        method: Optional[str] = TransferMethodType.STRIPE,
        retry: Optional[bool] = False,
    ):
        self.topic_name = "payment_stripe"
        self.task_type = PayoutTask.SUBMIT_TRANSFER
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
        # convert to submit transfer
        req_context = build_req_context(
            app_context, task_name="SubmitTransferTask", task_id=str(uuid4())
        )
        submit_transfer_request_dict = {}
        if "fn_kwargs" in data:
            data_kwargs = data["fn_kwargs"]
            for k, v in data_kwargs.items():
                submit_transfer_request_dict[k] = v

        submit_transfer_op_dict = {
            "transfer_repo": transfer_repo,
            "payment_account_repo": payment_account_repo,
            "stripe_transfer_repo": stripe_transfer_repo,
            "managed_account_transfer_repo": managed_account_transfer_repo,
            "transaction_repo": transaction_repo,
            "payment_account_edit_history_repo": payment_account_edit_history_repo,
            "stripe": req_context.stripe_async_client,
            "logger": req_context.log,
            "request": SubmitTransferRequest(**submit_transfer_request_dict),
        }
        submit_transfer_op = SubmitTransfer(**submit_transfer_op_dict)
        await submit_transfer_op.execute()
