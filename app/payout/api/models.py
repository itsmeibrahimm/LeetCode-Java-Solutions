from pydantic import BaseModel


class CreatePayoutAccountRequest(BaseModel):
    statement_descriptor: str
    entity: str
    account_type: str
