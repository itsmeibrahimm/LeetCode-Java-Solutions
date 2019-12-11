import inspect
from typing import Optional, List

from app.payout.core.transfer.tasks.base_task import BaseTask, normalize_task_arguments
from app.payout.models import PayoutTask, TransferMethodType


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
