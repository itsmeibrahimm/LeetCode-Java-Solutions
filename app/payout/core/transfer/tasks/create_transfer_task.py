import inspect
from typing import Optional, List
from uuid import uuid4

from app.commons.cache.cache import setup_cache
from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payout.core.transfer.processors.create_transfer import (
    CreateTransferRequest,
    CreateTransfer,
)
from app.payout.core.transfer.tasks.base_task import BaseTask, normalize_task_arguments
from app.payout.models import PayoutTask, TransferType
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


class CreateTransferTask(BaseTask):
    def __init__(
        self,
        payout_account_id: int,
        end_time: str,
        start_time: Optional[str],
        payout_countries: Optional[List[str]],
        created_by_id: Optional[int] = None,
        transfer_type: TransferType = TransferType.SCHEDULED,
        submit_after_creation: Optional[bool] = True,
    ):
        self.topic_name = "payment_payout"
        self.task_type = PayoutTask.CREATE_TRANSFER
        max_retries: int = 5
        attempts: int = 0
        fn_args: list = []
        super().__init__(
            self.topic_name,
            self.task_type,
            max_retries,
            attempts,
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

        # convert to create transfer
        req_context = build_req_context(
            app_context, task_name="CreateTransferTask", task_id=str(uuid4())
        )

        cache = setup_cache(app_context=app_context)

        create_transfer_request_dict = {}
        if "fn_kwargs" in data:
            data_kwargs = data["fn_kwargs"]
            for k, v in data_kwargs.items():
                create_transfer_request_dict[k] = v

        create_transfer_op_dict = {
            "transfer_repo": transfer_repo,
            "payment_account_repo": payment_account_repo,
            "stripe_transfer_repo": stripe_transfer_repo,
            "managed_account_transfer_repo": managed_account_transfer_repo,
            "transaction_repo": transaction_repo,
            "payment_account_edit_history_repo": payment_account_edit_history_repo,
            "stripe": req_context.stripe_async_client,
            "payment_lock_manager": app_context.redis_lock_manager,
            "kafka_producer": app_context.kafka_producer,
            "cache": cache,
            "logger": req_context.log,
            "request": CreateTransferRequest(**create_transfer_request_dict),
        }
        create_transfer_op = CreateTransfer(**create_transfer_op_dict)
        await create_transfer_op.execute()
