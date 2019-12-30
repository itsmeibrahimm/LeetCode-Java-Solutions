from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel

from app.payin.api.cart_payment.base.request import (
    ClientDescription,
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
)
from app.payin.core.payer.model import PayerCorrelationIds


class CorrelationIds(BaseModel):
    reference_id: str
    reference_type: str


class CreateCartPaymentRequest(CreateCartPaymentBaseRequest):
    payer_id: Optional[UUID]
    payment_method_id: UUID
    client_description: Optional[ClientDescription] = None
    correlation_ids: CorrelationIds
    metadata: Optional[Dict[str, Any]]
    payer_correlation_ids: Optional[PayerCorrelationIds]


class UpdateCartPaymentRequest(UpdateCartPaymentBaseRequest):
    pass
