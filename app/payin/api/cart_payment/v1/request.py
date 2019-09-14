from uuid import UUID

from app.payin.api.cart_payment.base.request import (
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
)


class CreateCartPaymentRequest(CreateCartPaymentBaseRequest):
    payer_id: UUID
    payment_method_id: UUID


class UpdateCartPaymentRequest(UpdateCartPaymentBaseRequest):
    payer_id: UUID
