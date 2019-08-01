from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel
from typing_extensions import final

from app.ledger.core.mx_transaction.types import MxTransactionType


class PaymentGatewayProviderCustomer(BaseModel):
    payment_provider: str
    payment_provider_customer_id: str


# https://pydantic-docs.helpmanual.io/#self-referencing-models
PaymentGatewayProviderCustomer.update_forward_refs()


@final
@dataclass(frozen=True)
class MxTransaction:
    mx_transaction_id: str
    payment_account_id: str
    amount: int
    currency: str
    ledger_id: str
    idempotency_key: str
    type: MxTransactionType
    created_at: datetime
    updated_at: datetime
    context: Optional[str] = None
    metadata: Optional[str] = None
