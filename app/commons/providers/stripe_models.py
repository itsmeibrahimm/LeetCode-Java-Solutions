from typing import Optional
from pydantic import BaseModel


class StripeSettings(BaseModel):
    api_key: str
    country: str
    api_version: Optional[str]


class CreateConnectedAccountToken(BaseModel):
    card: str
    stripe_account: str
    customer: str


class CreateBankAccountToken(BaseModel):
    ...


class CreateCreditCardToken(BaseModel):
    number: str
    exp_month: int
    exp_year: int
    cvc: str


class CreateCustomer(BaseModel):
    email: str
    description: str
