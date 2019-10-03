from uuid import UUID

from app.commons.api.models import PaymentRequest, PaymentResponse
from datetime import datetime
from typing import Optional
from app.ledger.core.types import MxTransactionType, MxScheduledLedgerIntervalType


class MxTransactionRequest(PaymentRequest):
    payment_account_id: str
    target_type: MxTransactionType
    amount: int
    currency: str
    idempotency_key: str
    routing_key: datetime
    interval_type: MxScheduledLedgerIntervalType
    target_id: Optional[str] = None
    context: Optional[dict] = None
    metadata: Optional[dict] = None
    legacy_transaction_id: Optional[str] = None


class MxTransaction(PaymentResponse):
    # pass
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
    context: Optional[dict]
    metadata: Optional[dict]
