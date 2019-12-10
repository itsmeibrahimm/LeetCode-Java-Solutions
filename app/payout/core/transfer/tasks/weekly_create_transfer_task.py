from typing import Optional, List

from app.payout.core.transfer.tasks.base_task import BaseTask
from app.payout.models import PayoutDay, PayoutCountry, PayoutTask


class WeeklyCreateTransferTask(BaseTask):
    payout_day: PayoutDay
    payout_countries: List[PayoutCountry]
    end_time: str
    unpaid_txn_start_time: str
    whitelist_payment_account_ids: List[int]
    exclude_recently_updated_accounts: Optional[bool] = False

    def __init__(
        self,
        payout_day: PayoutDay,
        payout_countries: List[PayoutCountry],
        end_time: str,
        unpaid_txn_start_time: str,
        whitelist_payment_account_ids: List[int],
        exclude_recently_updated_accounts: Optional[bool],
    ):
        self.fn_kwargs = {}
        self.topic_name = "payment_payout"
        self.task_type = PayoutTask.WEEKLY_CREATE_TRANSFER
        self.fn_kwargs["payout_day"] = payout_day
        self.fn_kwargs["payout_countries"] = payout_countries
        self.fn_kwargs["end_time"] = end_time
        self.fn_kwargs["unpaid_txn_start_time"] = unpaid_txn_start_time
        self.fn_kwargs["whitelist_payment_account_ids"] = whitelist_payment_account_ids
        self.fn_kwargs[
            "exclude_recently_updated_accounts"
        ] = exclude_recently_updated_accounts
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
