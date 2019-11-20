#  type: ignore

from datetime import datetime
from typing import Optional, List
from pydantic import Schema
from app.commons.api.models import PaymentRequest, PaymentResponse
from app.payout.models import PayoutTargetType, TransferId
from app.payout.repository.maindb.model.transfer import TransferStatus

__all__ = ["SubmitTransfer", "CreateTransfer", "SubmitTransferResponse", "Transfer"]


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
    end_time: datetime = Schema(default=..., description="End timestamp, required")
    start_time: Optional[datetime] = Schema(default=None, description="Start timestamp")
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


class SubmitTransferResponse(PaymentResponse):
    pass


class Transfer(PaymentResponse):
    id: TransferId = Schema(default=..., description="Transfer ID")
    subtotal: int = Schema(default=..., description="Subtotal of transfer")
    adjustments: str = Schema(default=..., description="Adjustments of transfer")
    amount: int = Schema(default=..., description="Amount of transfer")
    created_at: datetime = Schema(
        default=..., description="Timestamp transfer was created"
    )
    method: str = Schema(default=..., description="Payout method of transfer")
    recipient_id: Optional[int] = Schema(
        default=None, description="Recipient id of transfer"
    )
    currency: Optional[str] = Schema(default=None, description="Currency of transfer")
    submitted_at: Optional[datetime] = Schema(
        default=None, description="Timestamp transfer was submitted"
    )
    deleted_at: Optional[datetime] = Schema(
        default=None, description="Timestamp transfer was deleted"
    )
    manual_transfer_reason: Optional[str] = Schema(
        default=None, description="Manual transfer reason of transfer"
    )
    status: Optional[TransferStatus] = Schema(
        default=None, description="Transfer status"
    )
    status_code: Optional[str] = Schema(
        default=None, description="Transfer error status code"
    )
    submitting_at: Optional[datetime] = Schema(
        default=None, description="Timestamp transfer started submitting"
    )
    should_retry_on_failure: Optional[bool] = Schema(
        default=None, description="Boolean flag for retry failed transfer or not"
    )
    statement_description: Optional[str] = Schema(
        default=None, description="Statement description of transfer"
    )
    created_by_id: Optional[int] = Schema(
        default=None, description="User id that created the transfer"
    )
    deleted_by_id: Optional[int] = Schema(
        default=None, description="User id that deleted the transfer"
    )
    payment_account_id: Optional[int] = Schema(
        default=None, description="Payment account id of transfer"
    )
    recipient_ct_id: Optional[int] = Schema(
        default=None, description="Recipient content type id of transfer"
    )
    submitted_by_id: Optional[int] = Schema(
        default=None, description="User id that submitted the transfer"
    )


class TransferList(PaymentResponse):
    count: int = Schema(default=..., description="Number of results")
    transfer_list: List[Transfer] = Schema(default=..., description="List of transfers")
