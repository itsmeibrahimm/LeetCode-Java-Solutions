from app.payin.core.types import LegacyPaymentInfo, CountryCode
from app.payin.api.cart_payment.base.request import (
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
)


class CreateCartPaymentLegacyRequest(CreateCartPaymentBaseRequest):
    payer_country: CountryCode = CountryCode.US
    legacy_payment: LegacyPaymentInfo


class UpdateCartPaymentLegacyRequest(UpdateCartPaymentBaseRequest):
    payer_country: CountryCode = CountryCode.US
