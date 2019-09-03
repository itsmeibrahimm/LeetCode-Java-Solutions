from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.cart_payment.types import CartType
from app.payin.core.types import LegacyPaymentInfo


# Our Mypy type checking does not currently support Schema objects.


class SplitPayment(BaseModel):
    payout_account_id: str
    application_fee_amount: int


class CartMetadata(BaseModel):
    reference_id: int
    ct_reference_id: int
    type: CartType


class CreateCartPaymentRequest(BaseModel):
    payer_id: Optional[str] = None
    amount: int
    payer_country: CountryCode = CountryCode.US
    payment_country: CountryCode
    currency: str
    payment_method_id: Optional[str] = None
    delay_capture: bool
    idempotency_key: str
    client_description: Optional[str] = None
    payer_statement_description: Optional[str] = None
    legacy_payment: Optional[LegacyPaymentInfo] = None
    split_payment: Optional[SplitPayment] = None
    metadata: CartMetadata


class UpdateCartPaymentRequest(BaseModel):
    idempotency_key: str
    payer_id: str
    amount: int
    payer_country: CountryCode = CountryCode.US
    legacy_payment: Optional[LegacyPaymentInfo] = None
    client_description: Optional[str] = None
