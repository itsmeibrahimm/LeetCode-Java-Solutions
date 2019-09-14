from uuid import UUID
from typing import Optional, Dict, Any

from pydantic import BaseModel

from app.payin.api.cart_payment.base.request import (
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
)


class CorrelationIds(BaseModel):
    reference_id: str
    reference_type: str


class CreateCartPaymentRequest(CreateCartPaymentBaseRequest):
    payer_id: UUID
    payment_method_id: UUID
    correlation_ids: CorrelationIds
    metadata: Optional[Dict[str, Any]]


class UpdateCartPaymentRequest(UpdateCartPaymentBaseRequest):
    payer_id: UUID
