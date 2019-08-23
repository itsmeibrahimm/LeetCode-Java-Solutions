from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Json
from typing_extensions import final

from app.ledger.core.types import MxTransactionType, MxScheduledLedgerIntervalType


class MxTransactionModel(BaseModel):
    class Config:
        allow_mutation = False
        orm_mode = True


@final
class MxTransaction(MxTransactionModel):
    id: UUID
    payment_account_id: str
    amount: int
    currency: str
    ledger_id: UUID
    idempotency_key: str
    routing_key: datetime
    target_type: MxTransactionType
    legacy_transaction_id: Optional[str]
    target_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    context: Optional[Json]
    metadata: Optional[Json]


# todo：refactor this into new folder later
@final
class MxScheduledLedger(MxTransactionModel):
    id: UUID
    payment_account_id: str
    ledger_id: UUID
    interval_type: MxScheduledLedgerIntervalType
    start_time: datetime
    end_time: datetime
    closed_at: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
