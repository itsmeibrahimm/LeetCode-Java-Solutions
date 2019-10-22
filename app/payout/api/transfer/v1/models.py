from datetime import datetime
from typing import Optional, List
from app.commons.api.models import PaymentRequest, PaymentResponse
from app.payout.types import PayoutTargetType, PayoutDay

__all__ = ["SubmitTransfer", "CreateTransfer", "Transfer", "WeeklyCreateTransfer"]


class SubmitTransfer(PaymentRequest):
    statement_descriptor: str
    target_id: Optional[str]
    target_type: Optional[PayoutTargetType]
    method: Optional[str]
    retry: Optional[bool]
    submitted_by: Optional[int]


class CreateTransfer(PaymentRequest):
    payout_account_id: int
    transfer_type: str
    bank_info_recently_changed: bool
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    target_id: Optional[int]
    target_type: Optional[PayoutTargetType]
    target_business_id: Optional[int]
    payout_countries: Optional[List[str]]


class WeeklyCreateTransfer(PaymentRequest):
    payout_day: PayoutDay
    end_time: datetime
    payout_countries: List[str]
    unpaid_txn_start_time: Optional[datetime]
    start_time: Optional[datetime]
    exclude_recently_updated_accounts: Optional[bool]


class Transfer(PaymentResponse):
    pass
