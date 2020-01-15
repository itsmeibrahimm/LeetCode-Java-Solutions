import inspect
from uuid import uuid4

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payout.core.transfer.processors.update_transfer_by_stripe_transfer_status import (
    UpdateTransferByStripeTransferStatusRequest,
    UpdateTransferByStripeTransferStatus,
)
from app.payout.core.transfer.tasks.base_task import BaseTask, normalize_task_arguments
from app.payout.models import PayoutTask
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository


class MonitorTransferWithIncorrectStatusTask(BaseTask):
    def __init__(self, transfer_id: int):
        self.topic_name = "payment_stripe"
        self.task_type = PayoutTask.MONITOR_TRANSFER_WITH_INCORRECT_STATUS
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
        stripe_transfer_repo = StripeTransferRepository(
            database=app_context.payout_maindb
        )
        # convert to monitor transfer with incorrect status
        req_context = build_req_context(
            app_context,
            task_name="MonitorTransferWithIncorrectStatusTask",
            task_id=str(uuid4()),
        )
        monitor_transfer_request_dict = {}
        if "fn_kwargs" in data:
            data_kwargs = data["fn_kwargs"]
            for k, v in data_kwargs.items():
                monitor_transfer_request_dict[k] = v

        update_transfer_by_stripe_transfer_op_dict = {
            "transfer_repo": transfer_repo,
            "stripe_transfer_repo": stripe_transfer_repo,
            "stripe": req_context.stripe_async_client,
            "logger": req_context.log,
            "request": UpdateTransferByStripeTransferStatusRequest(
                **monitor_transfer_request_dict
            ),
        }
        update_transfer_by_stripe_transfer_op = UpdateTransferByStripeTransferStatus(
            **update_transfer_by_stripe_transfer_op_dict
        )
        await update_transfer_by_stripe_transfer_op.execute()
