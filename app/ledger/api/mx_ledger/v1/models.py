from datetime import datetime
from typing import Optional
from uuid import UUID

from app.commons.api.models import PaymentResponse, PaymentRequest
from app.commons.types import Currency
from app.ledger.core.types import MxLedgerType, MxLedgerStateType


class MxLedger(PaymentResponse):
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


class MxLedgerRequest(PaymentRequest):
    payment_account_id: str
    currency: str
    balance: int
    type: str
