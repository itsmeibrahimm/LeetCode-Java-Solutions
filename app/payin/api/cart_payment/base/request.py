from typing import Optional

from pydantic import BaseModel, PositiveInt

from app.commons.types import CountryCode, CurrencyType
from app.commons.types import CountryCode


class SplitPayment(BaseModel):
    payout_account_id: str
    application_fee_amount: int


class CreateCartPaymentBaseRequest(BaseModel):
    amount: PositiveInt
    payment_country: CountryCode
    currency: CurrencyType
    delay_capture: bool
    idempotency_key: str
    client_description: Optional[str] = None
    payer_statement_description: Optional[str] = None
    split_payment: Optional[SplitPayment] = None


class UpdateCartPaymentBaseRequest(BaseModel):
    idempotency_key: str
    amount: PositiveInt
    client_description: Optional[str] = None
