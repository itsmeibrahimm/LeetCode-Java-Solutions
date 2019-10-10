from typing import Optional
from app.commons.api.models import PaymentRequest

__all__ = ["SubmitTransfer"]


class SubmitTransfer(PaymentRequest):
    retry: Optional[bool]
    submitted_by: Optional[int]
