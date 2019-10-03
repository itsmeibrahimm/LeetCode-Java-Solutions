from datetime import datetime
from typing import Optional

from uuid import UUID

from app.commons.core.processor import OperationResponse
from app.commons.types import Currency
from app.ledger.core.types import MxLedgerType, MxLedgerStateType


class MxLedgerInternal(OperationResponse):
    # todo: some fields might need to be removed, we don't want expose unnecessary data to client side
    id: UUID
    type: MxLedgerType
    currency: Currency
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
