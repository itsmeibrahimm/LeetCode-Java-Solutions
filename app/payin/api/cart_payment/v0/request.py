from app.payin.core.types import LegacyPaymentInfo, CountryCode
from typing import Dict, Any

from app.payin.core.cart_payment.model import LegacyCorrelationIds
from app.payin.core.types import LegacyPaymentInfo
from app.payin.api.cart_payment.base.request import (
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
)


class CreateCartPaymentLegacyRequest(CreateCartPaymentBaseRequest):
    payer_country: CountryCode = CountryCode.US
    legacy_payment: LegacyPaymentInfo
    legacy_correlation_ids: LegacyCorrelationIds
    legacy_stripe_metadata: Dict[str, Any]


class UpdateCartPaymentLegacyRequest(UpdateCartPaymentBaseRequest):
    payer_country: CountryCode = CountryCode.US
