from datetime import datetime
from typing import List, Optional

from app.commons.core.processor import OperationResponse
from app.commons.types import Currency
from app.payout import types


class TransactionInternal(OperationResponse):
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
    # there are multiple types of metadata in db that we need to clean up
    # use str to avoid 500 caused by ValidationError
    metadata: Optional[str]
    created_at: datetime
    inserted_at: Optional[datetime]
    updated_at: datetime


class TransactionListInternal(OperationResponse):
    data: List[TransactionInternal]
    count: int
    new_offset: Optional[int]
