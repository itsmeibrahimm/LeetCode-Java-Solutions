import inspect
from typing import Optional, List

from app.payout.core.transfer.tasks.base_task import BaseTask, normalize_task_arguments
from app.payout.models import PayoutDay, PayoutCountry, PayoutTask


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
