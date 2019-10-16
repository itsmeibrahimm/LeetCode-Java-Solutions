from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.commons.api.models import PaymentResponse, PaymentRequest
from app.commons.types import Currency
import app.payout.types as types


class Transaction(PaymentResponse):
    id: int
    amount: int
    amount_paid: int
    payout_account_id: int
    transfer_id: Optional[int]
    payout_id: Optional[int]
    created_by_id: Optional[int]
    target_id: Optional[int]
    target_type: Optional[str]
    currency: Optional[Currency]
    idempotency_key: Optional[str]
    state: Optional[types.TransactionState]
    notes: Optional[str]
    metadata: Optional[dict]
    created_at: datetime
    inserted_at: Optional[datetime]
    updated_at: datetime


class TransactionList(PaymentResponse):
    count: int
    transaction_list: List[Transaction]


class TransactionCreate(PaymentRequest):
    #
    # required fields
    #
    amount: int
    payment_account_id: int
    idempotency_key: str
    currency: Currency
    target_id: int
    target_type: str

    #
    # optional fields
    #
    amount_paid: Optional[
        int
    ] = None  # Biz layer will default it to 0, same default behavior as DSJ
    created_by_id: Optional[int] = None
    notes: Optional[str] = None
    metadata: Optional[str] = None


class ReverseTransaction(PaymentRequest):
    transaction_id: types.TransactionId
    reverse_reason: Optional[str]


class TimeRange(BaseModel):
    start_time: datetime
    end_time: datetime
