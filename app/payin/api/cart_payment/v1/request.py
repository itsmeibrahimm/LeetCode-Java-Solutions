from uuid import UUID
from typing import Optional, Dict, Any

from pydantic import BaseModel

from app.payin.api.cart_payment.base.request import (
    CreateCartPaymentBaseRequest,
    UpdateCartPaymentBaseRequest,
    ClientDescription,
)
from app.payin.core.types import PayerReferenceIdType


class CorrelationIds(BaseModel):
    reference_id: str
    reference_type: str


class CreateCartPaymentRequest(CreateCartPaymentBaseRequest):
    payer_id: UUID
    payment_method_id: UUID
    client_description: Optional[ClientDescription] = None
    correlation_ids: CorrelationIds
    metadata: Optional[Dict[str, Any]]
    payer_reference_id: Optional[str]
    payer_reference_id_type: Optional[PayerReferenceIdType]


class UpdateCartPaymentRequest(UpdateCartPaymentBaseRequest):
    pass
