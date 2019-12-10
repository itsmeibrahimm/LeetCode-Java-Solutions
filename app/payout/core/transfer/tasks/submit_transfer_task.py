from typing import Optional, List

from app.payout.core.transfer.tasks.base_task import BaseTask
from app.payout.models import PayoutTask, TransferMethodType


class SubmitTransferTask(BaseTask):
    transfer_id: int
    method: Optional[str] = TransferMethodType.STRIPE
    retry: Optional[bool] = False
    submitted_by: Optional[int]

    def __init__(
        self,
        transfer_id: int,
        method: Optional[str],
        retry: Optional[bool],
        submitted_by: Optional[int],
    ):
        self.fn_kwargs = {}
        self.topic_name = "payment_stripe"
        self.task_type = PayoutTask.SUBMIT_TRANSFER
        self.fn_kwargs["transfer_id"] = transfer_id
        self.fn_kwargs["method"] = method
        self.fn_kwargs["retry"] = retry
        self.fn_kwargs["submitted_by"] = submitted_by
        auto_retry_for: List[Exception] = []
        max_retries: int = 0
        fn_args: list = []
        super().__init__(
            self.topic_name,
            self.task_type,
            auto_retry_for,
            max_retries,
            fn_args,
            self.fn_kwargs,
        )
