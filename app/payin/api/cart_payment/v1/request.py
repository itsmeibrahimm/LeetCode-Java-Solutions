from pydantic import BaseModel
from typing import Optional

from app.commons.types import CountryCode
from app.payin.core.types import PayerIdType, PaymentMethodIdType
from app.payin.core.cart_payment.types import CaptureMethod, CartType


# Our Mypy type checking does not currently support Schema objects.


class LegacyPayment(BaseModel):
    consumer_id: int
    stripe_customer_id: int
    charge_id: int


class SplitPayment(BaseModel):
    payout_account_id: str
    appication_fee_amount: int


class CartMetadata(BaseModel):
    reference_id: int
    ct_reference_id: int
    type: CartType


class CreateCartPaymentRequest(BaseModel):
    payer_id: str
    payer_id_type: PayerIdType = PayerIdType.DD_PAYMENT_PAYER_ID
    amount: int
    payer_country: CountryCode = CountryCode.US
    payment_country: CountryCode
    currency: str
    payment_method_id: str
    payment_method_id_type: PaymentMethodIdType = PaymentMethodIdType.DD_PAYMENT_METHOD_ID
    capture_method: CaptureMethod = CaptureMethod.AUTO
    idempotency_key: str
    client_description: Optional[str] = None
    payer_statement_description: Optional[str] = None
    legacy_payment: Optional[LegacyPayment] = None
    split_payment: Optional[SplitPayment] = None
    metadata: CartMetadata


class UpdateCartPaymentRequest(BaseModel):
    idempotency_key: str
    payer_id: str
    payer_id_type: PayerIdType = PayerIdType.DD_PAYMENT_PAYER_ID
    amount: int
    payer_country: CountryCode = CountryCode.US
    metadata: Optional[CartMetadata] = None
    legacy_payment: Optional[LegacyPayment] = None
    client_description: Optional[str] = None
    payer_statement_description: Optional[str] = None
