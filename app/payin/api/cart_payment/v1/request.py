from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.cart_payment.types import CartType
from app.payin.core.types import LegacyPaymentInfo, MixedUuidStrType


# Our Mypy type checking does not currently support Schema objects.


class SplitPayment(BaseModel):
    payout_account_id: str
    application_fee_amount: int


class CartMetadata(BaseModel):
    reference_id: int
    ct_reference_id: int
    type: CartType


class CreateCartPaymentBaseRequest(BaseModel):
    amount: int
    payer_country: CountryCode = CountryCode.US
    payment_country: CountryCode
    currency: str
    delay_capture: bool
    idempotency_key: str
    client_description: Optional[str] = None
    payer_statement_description: Optional[str] = None
    split_payment: Optional[SplitPayment] = None
    metadata: CartMetadata


class CreateCartPaymentRequest(CreateCartPaymentBaseRequest):
    payer_id: MixedUuidStrType
    payment_method_id: MixedUuidStrType


class CreateCartPaymentLegacyRequest(CreateCartPaymentBaseRequest):
    legacy_payment: LegacyPaymentInfo


class UpdateCartPaymentBaseRequest(BaseModel):
    idempotency_key: str
    amount: int
    payer_country: CountryCode = CountryCode.US
    client_description: Optional[str] = None


class UpdateCartPaymentRequest(UpdateCartPaymentBaseRequest):
    payer_id: Optional[str]


class UpdateCartPaymentLegacyRequest(UpdateCartPaymentBaseRequest):
    legacy_payment: Optional[LegacyPaymentInfo] = None
