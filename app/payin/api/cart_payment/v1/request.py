from typing import Optional

from app.payin.core.types import MixedUuidStrType
from app.payin.api.cart_payment.base.request import (
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
)


# Our Mypy type checking does not currently support Schema objects.


class CreateCartPaymentRequest(CreateCartPaymentBaseRequest):
    payer_id: MixedUuidStrType
    payment_method_id: MixedUuidStrType


class UpdateCartPaymentRequest(UpdateCartPaymentBaseRequest):
    payer_id: Optional[str]
