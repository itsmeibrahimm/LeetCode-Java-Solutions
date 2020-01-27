from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Schema

from app.commons.types import PgpCode
from app.payin.api.cart_payment.base.request import (
    ClientDescription,
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
)
from app.payin.core.payer.model import PayerCorrelationIds


class CorrelationIds(BaseModel):
    reference_id: str = Schema(  # type: ignore
        default=..., description="client provided correlation id for the cart payment"
    )
    reference_type: str = Schema(  # type: ignore
        default=..., description="client provided correlation id type"
    )


class PaymentMethodToken(BaseModel):
    token: str = Schema(  # type: ignore
        default=...,
        description="one-time token to identify a payment method tokenized by payment gateway",
    )
    payment_gateway: PgpCode = Schema(  # type: ignore
        default=..., description="payment gateway which tokenized this payment method"
    )


class CreateCartPaymentRequestV1(CreateCartPaymentBaseRequest):
    payer_id: Optional[UUID] = Schema(  # type: ignore
        default=..., description="id of payer for this payment."
    )
    payment_method_id: Optional[UUID] = Schema(  # type: ignore
        default=..., description="id of payment method used for this payment."
    )
    payment_method_token: Optional[PaymentMethodToken] = Schema(  # type: ignore
        default=...,
        description="one-time payment method token issued by payment gateway.",
    )
    dd_stripe_card_id: Optional[int] = Schema(  # type: ignore
        default=..., description="id of legacy stripe card as payment method"
    )
    client_description: Optional[ClientDescription] = Schema(  # type: ignore
        default=None, description="client description of this payment"
    )
    correlation_ids: CorrelationIds = Schema(  # type: ignore
        default=..., description="client provided correlation ids of this payment"
    )
    metadata: Optional[Dict[str, Any]] = Schema(  # type: ignore
        default=...,
        description="metadata of this payment to be persisted in payment system",
    )
    payer_correlation_ids: Optional[PayerCorrelationIds] = Schema(  # type: ignore
        default=...,
        description="client provided payer correlation id used to identify a payer",
    )


class UpdateCartPaymentRequestV1(UpdateCartPaymentBaseRequest):
    pass
