from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Schema

from app.commons.types import PgpCode
from app.payin.api.payer.v1.request import CreatePayerRequest
from app.payin.core.payer.model import PayerCorrelationIds


class CreatePaymentMethodRequestV1(BaseModel):
    payer_id: Optional[UUID] = Schema(  # type: ignore
        default=..., description="identity of payer."
    )
    payer_correlation_ids: Optional[PayerCorrelationIds] = Schema(  # type: ignore
        default=..., description="external identity of payer."
    )
    create_payer_request: Optional[CreatePayerRequest] = Schema(  # type: ignore
        default=..., description="detailed information to create payer."
    )
    payment_gateway: PgpCode = Schema(  # type: ignore
        default=PgpCode.STRIPE, description="payment provider."
    )
    token: str = Schema(  # type: ignore
        default=...,
        description="one-time payment payment token issued by payment provider.",
    )
    set_default: bool = Schema(  # type: ignore
        default=..., description="true if set the new payment method to default card."
    )
    is_scanned: bool = Schema(  # type: ignore
        default=...,
        description="true if the payment method is already scanned by fraud.",
    )
    is_active: bool = Schema(  # type: ignore
        default=...,
        description="true if the payment method is already active by fraud.",
    )
