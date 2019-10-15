from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.commons.api.models import PaymentResponse
from app.commons.types import Currency
from app.payout.types import TransactionState


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
    state: Optional[TransactionState]
    notes: Optional[str]
    metadata: Optional[dict]
    created_at: datetime
    inserted_at: Optional[datetime]
    updated_at: datetime


class TransactionList(PaymentResponse):
    count: int
    transaction_list: List[Transaction]


class TimeRange(BaseModel):
    start_time: datetime
    end_time: datetime
