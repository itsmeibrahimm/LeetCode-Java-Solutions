from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from typing_extensions import final

from app.commons.types import CurrencyType
from app.ledger.core.mx_transaction.types import (
    MxTransactionType,
    MxLedgerType,
    MxLedgerStateType,
    MxScheduledLedgerIntervalType,
)


class PaymentGatewayProviderCustomer(BaseModel):
    payment_provider: str
    payment_provider_customer_id: str


# https://pydantic-docs.helpmanual.io/#self-referencing-models
PaymentGatewayProviderCustomer.update_forward_refs()


@final
@dataclass(frozen=True)
class MxTransaction:
    mx_transaction_id: UUID
    payment_account_id: str
    amount: int
    currency: str
    ledger_id: str
    idempotency_key: str
    routing_key: datetime
    target_type: MxTransactionType
    legacy_transaction_id: Optional[str]
    target_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    context: Optional[str] = None
    metadata: Optional[str] = None


# todo：refactor this into new folder later
@final
@dataclass(frozen=True)
class MxLedger:
    mx_ledger_id: UUID
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
    finalized_at: Optional[datetime] = None
    created_by_employee_id: Optional[str] = None
    submitted_by_employee_id: Optional[str] = None
    rolled_to_ledger_id: Optional[str] = None


@final
@dataclass(frozen=True)
class MxScheduledLedger:
    mx_scheduled_ledger_id: UUID
    payment_account_id: str
    ledger_id: UUID
    interval_type: MxScheduledLedgerIntervalType
    start_time: datetime
    end_time: datetime
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
