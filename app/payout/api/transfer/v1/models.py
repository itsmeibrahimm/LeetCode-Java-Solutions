from datetime import datetime
from typing import Optional, List
from app.commons.api.models import PaymentRequest, PaymentResponse
from app.payout.types import PayoutTargetType, PayoutDay

__all__ = ["SubmitTransfer", "CreateTransfer", "Transfer"]


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
    payout_day: Optional[PayoutDay]
    payout_countries: Optional[List[str]]


class Transfer(PaymentResponse):
    pass
