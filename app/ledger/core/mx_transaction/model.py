from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Json
from typing_extensions import final

from app.commons.database.model import DBEntity
from app.commons.types import CurrencyType
from app.ledger.core.mx_transaction.types import (
    MxTransactionType,
    MxLedgerType,
    MxLedgerStateType,
    MxScheduledLedgerIntervalType,
)


@final
class MxTransaction(DBEntity):
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
class MxLedger(DBEntity):
    id: UUID
    type: MxLedgerType
    currency: CurrencyType
    state: MxLedgerStateType
    balance: int
    payment_account_id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    submitted_at: Optional[datetime]
    amount_paid: Optional[int]
    legacy_transfer_id: Optional[str]
    finalized_at: Optional[datetime]
    created_by_employee_id: Optional[str]
    submitted_by_employee_id: Optional[str]
    rolled_to_ledger_id: Optional[str]


@final
class MxScheduledLedger(DBEntity):
    id: UUID
    payment_account_id: str
    ledger_id: UUID
    interval_type: MxScheduledLedgerIntervalType
    start_time: datetime
    end_time: datetime
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
