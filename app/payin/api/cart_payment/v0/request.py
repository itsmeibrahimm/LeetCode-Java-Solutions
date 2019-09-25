from app.commons.types import CountryCode
from app.payin.api.cart_payment.base.request import (
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
)
from app.payin.core.cart_payment.model import CorrelationIds
from app.payin.core.types import LegacyPaymentInfo


class CreateCartPaymentLegacyRequest(CreateCartPaymentBaseRequest):
    payer_country: CountryCode = CountryCode.US
    legacy_payment: LegacyPaymentInfo
    legacy_correlation_ids: CorrelationIds


class UpdateCartPaymentLegacyRequest(UpdateCartPaymentBaseRequest):
    amount: int  # Amount is overriden here to allow negative values as for v0 it is a delta
    legacy_payment: LegacyPaymentInfo
