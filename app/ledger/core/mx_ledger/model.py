from datetime import datetime
from typing import Optional
from uuid import UUID

from typing_extensions import final
from pydantic import BaseModel

from app.commons.types import CurrencyType
from app.ledger.core.types import MxLedgerType, MxLedgerStateType


class MxLedgerModel(BaseModel):
    class Config:
        allow_mutation = False
        orm_mode = True


@final
class MxLedger(MxLedgerModel):
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
    rolled_to_ledger_id: Optional[UUID]
