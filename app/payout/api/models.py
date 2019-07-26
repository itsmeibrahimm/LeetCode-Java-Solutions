from pydantic import BaseModel

from app.commons.types import CountryCode


class CreatePayoutAccountRequest(BaseModel):
    statement_descriptor: str
    entity: str
    account_type: str


class CreateStripeManagedAccountRequest(BaseModel):
    stripe_id: str
    country_code: CountryCode
