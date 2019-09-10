from typing import Optional

from app.payin.core.types import LegacyPaymentInfo
from app.payin.api.cart_payment.base.request import (
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
)


class CreateCartPaymentLegacyRequest(CreateCartPaymentBaseRequest):
    legacy_payment: LegacyPaymentInfo


class UpdateCartPaymentLegacyRequest(UpdateCartPaymentBaseRequest):
    legacy_payment: Optional[LegacyPaymentInfo] = None
