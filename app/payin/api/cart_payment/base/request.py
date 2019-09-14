from typing import Optional

from pydantic import BaseModel, PositiveInt

from app.commons.types import CountryCode, CurrencyType
from app.payin.core.cart_payment.types import CartType


class SplitPayment(BaseModel):
    payout_account_id: str
    application_fee_amount: int


class CartMetadata(BaseModel):
    reference_id: str
    reference_type: str
    type: CartType


class CreateCartPaymentBaseRequest(BaseModel):
    amount: PositiveInt
    payment_country: CountryCode
    currency: CurrencyType
    delay_capture: bool
    idempotency_key: str
    client_description: Optional[str] = None
    payer_statement_description: Optional[str] = None
    split_payment: Optional[SplitPayment] = None
    cart_metadata: CartMetadata


class UpdateCartPaymentBaseRequest(BaseModel):
    idempotency_key: str
    amount: PositiveInt
    client_description: Optional[str] = None
