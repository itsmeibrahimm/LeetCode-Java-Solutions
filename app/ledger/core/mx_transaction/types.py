from datetime import datetime
from typing import Optional
from uuid import UUID
from app.commons.core.processor import OperationResponse


class MxTransactionInternal(OperationResponse):
    # todo: some fields might need to be removed, we don't want expose unnecessary data to client side
    id: UUID
    payment_account_id: str
    amount: int
    currency: str
    ledger_id: UUID
    idempotency_key: str
    target_type: str  # todo: update all wrong types to Enum
    routing_key: datetime
    target_id: Optional[str]
    legacy_transaction_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    context: Optional[dict]
    metadata: Optional[dict]
