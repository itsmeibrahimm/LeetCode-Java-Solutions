from pydantic import BaseModel


class CreateMxLedgerRequest(BaseModel):
    balance: int
    currency: str
    payment_account_id: str
    type: str


# https://pydantic-docs.helpmanual.io/#self-referencing-models
CreateMxLedgerRequest.update_forward_refs()
