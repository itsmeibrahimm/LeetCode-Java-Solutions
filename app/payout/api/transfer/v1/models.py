from typing import Optional
from app.commons.api.models import PaymentRequest
from app.payout.types import PayoutTargetType

__all__ = ["SubmitTransfer"]


class SubmitTransfer(PaymentRequest):
    statement_descriptor: str
    target_id: Optional[str]
    target_type: Optional[PayoutTargetType]
    method: Optional[str]
    retry: Optional[bool]
    submitted_by: Optional[int]
