from datetime import datetime
from typing import Optional, List

from app.payout.core.transfer.tasks.base_task import BaseTask
from app.payout.models import PayoutTask, TransferType, PayoutCountry


class CreateTransferTask(BaseTask):
    payout_account_id: int
    transfer_type: TransferType = TransferType.SCHEDULED
    end_time: datetime
    start_time: Optional[datetime]
    payout_countries: Optional[List[PayoutCountry]]
    created_by_id: Optional[int]

    def __init__(
        self,
        payout_account_id: int,
        end_time: datetime,
        transfer_type: TransferType,
        start_time: Optional[datetime],
        payout_countries: Optional[List[PayoutCountry]],
        created_by_id: Optional[int],
    ):
        self.fn_kwargs = {}
        self.topic_name = "payment_payout"
        self.task_type = PayoutTask.CREATE_TRANSFER
        self.fn_kwargs["payout_account_id"] = payout_account_id
        self.fn_kwargs["payout_countries"] = payout_countries
        self.fn_kwargs["end_time"] = end_time
        self.fn_kwargs["transfer_type"] = transfer_type
        self.fn_kwargs["start_time"] = start_time
        self.fn_kwargs["created_by_id"] = created_by_id
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
