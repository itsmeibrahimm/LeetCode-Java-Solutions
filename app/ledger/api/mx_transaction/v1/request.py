from pydantic import BaseModel

from app.ledger.core.mx_transaction.types import MxTransactionType


class CreateMxTransactionRequest(BaseModel):
    payment_account_id: str
    type: MxTransactionType
    amount: str
    currency: str
    idempotency_key: str
    context: str
    metadata: str


# https://pydantic-docs.helpmanual.io/#self-referencing-models
CreateMxTransactionRequest.update_forward_refs()
