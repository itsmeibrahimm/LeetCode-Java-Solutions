#  type: ignore

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Schema

from app.commons.api.models import PaymentResponse, PaymentRequest
from app.commons.types import Currency
import app.payout.models as types


################################
# Data Model for API requests  #
################################


class TransactionCreate(PaymentRequest):
    """
    Request model for creating a transaction
    """

    #
    # required fields
    #
    amount: int = Schema(default=..., description="The amount of transaction in cents")
    payment_account_id: int = Schema(
        default=...,
        description="The payment account id under which the transaction to be created",
    )
    idempotency_key: str = Schema(
        default=..., description="The idempotency key for the transaction to be created"
    )
    currency: Currency = Schema(
        default=..., description="The currency code for the transaction to be created"
    )
    target_id: int = Schema(
        default=...,
        description="The target id (e.g., delivery id) for the transaction to be created",
    )
    target_type: str = Schema(
        default=...,
        description="The target type (e.g., delivery) for the transaction to be created",
    )

    #
    # optional fields
    #
    amount_paid: Optional[int] = Schema(
        default=None,
        description="(Optional) The amount of fund has been transferred to the destination stripe account",
    )  # Biz layer will default it to 0, same default behavior as DSJ

    created_by_id: Optional[int] = Schema(
        default=None, description="(Optional) User id who created the transaction"
    )
    notes: Optional[str] = Schema(
        default=None, description="(Optional) Notes for the transaction"
    )
    metadata: Optional[str] = Schema(
        default=None, description="(Optional) a JSON str of metadata"
    )


class ReverseTransaction(PaymentRequest):
    """
    Request model for reversing a transaction
    """

    reverse_reason: Optional[str] = Schema(
        default=None, description="(Optional) Reason for this reversal"
    )


################################
# Data Model for API response  #
################################


class Transaction(PaymentResponse):
    id: int = Schema(default=..., description="Transaction ID")
    amount: int = Schema(default=..., description="Transaction amount in cents")
    amount_paid: int = Schema(
        default=...,
        description="Amount transferred to stripe destination account in cents",
    )
    payout_account_id: int = Schema(
        default=..., description="Payment account id (will be renamed)"
    )
    transfer_id: Optional[int] = Schema(
        default=None, description="Associated transfer ID"
    )
    payout_id: Optional[int] = Schema(default=None, description="Associated payout ID")
    created_by_id: Optional[int] = Schema(
        default=None, description="User ID who created the transaction"
    )
    target_id: Optional[int] = Schema(
        default=None, description="The target id (e.g., delivery id) of the transaction"
    )
    target_type: Optional[str] = Schema(
        default=None, description="The target type (e.g., delivery) of the transaction"
    )
    currency: Optional[Currency] = Schema(
        default=None, description="The currency code of the transaction"
    )
    idempotency_key: Optional[str] = Schema(
        default=None, description="The idempotency key of the transaction"
    )
    state: Optional[types.TransactionState] = Schema(
        default=None, description="The state of the transaction"
    )
    notes: Optional[str] = Schema(
        default=None, description="Notes about the transaction"
    )
    metadata: Optional[str] = Schema(default=None, description="JSON str of metadata")
    created_at: datetime = Schema(
        default=None, description="Timestamp when the transaction was created"
    )
    inserted_at: Optional[datetime] = Schema(
        default=None, description="Timestamp when the transaction was inserted"
    )
    updated_at: datetime = Schema(
        default=None, description="Timestamp when the transaction was updated"
    )


class TransactionList(PaymentResponse):
    count: int = Schema(default=..., description="Number of results")
    transaction_list: List[Transaction] = Schema(
        default=..., description="List of transactions"
    )


##################
# Aux Data Model #
##################


class TimeRange(BaseModel):
    start_time: datetime
    end_time: datetime
