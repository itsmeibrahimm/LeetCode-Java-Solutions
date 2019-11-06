#  type: ignore

from datetime import datetime
from typing import Optional, List
from pydantic import Schema
from app.commons.api.models import PaymentRequest, PaymentResponse
from app.payout.models import PayoutTargetType

__all__ = ["SubmitTransfer", "CreateTransfer", "Transfer"]


class SubmitTransfer(PaymentRequest):
    """
    Request model for submit a transfer
    """

    statement_descriptor: str = Schema(
        default=..., description="Statement descriptor for this transfer"
    )
    target_id: Optional[int] = Schema(default=None, description="Target ID")
    target_type: Optional[PayoutTargetType] = Schema(
        default=None, description="Target type"
    )
    method: Optional[str] = Schema(
        default=None, description="Submit method (e.g., stripe, doordash_pay)"
    )
    retry: Optional[bool] = Schema(
        default=None, description="True if this is a retry submission"
    )
    submitted_by: Optional[int] = Schema(
        default=None, description="Submitted by user ID"
    )


class CreateTransfer(PaymentRequest):
    """
    Request model for creating a new transfer
    """

    payout_account_id: int = Schema(default=..., description="Payout account ID")
    transfer_type: str = Schema(default=..., description="Transfer type")
    start_time: Optional[datetime] = Schema(default=None, description="Start timestamp")
    end_time: Optional[datetime] = Schema(default=None, description="End timestamp")
    target_id: Optional[int] = Schema(default=None, description="Target ID")
    target_type: Optional[PayoutTargetType] = Schema(
        default=None, description="Target type"
    )
    target_business_id: Optional[int] = Schema(
        default=None, description="Target business ID"
    )
    payout_countries: Optional[List[str]] = Schema(
        default=None, description="Payout countries"
    )
    created_by_id: Optional[int] = Schema(
        default=None, description="User id that creates the manual transfer"
    )


class Transfer(PaymentResponse):
    pass
