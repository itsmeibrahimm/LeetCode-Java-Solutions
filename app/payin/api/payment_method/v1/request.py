from uuid import UUID

from pydantic import BaseModel

from app.commons.types import PgpCode


class CreatePaymentMethodRequestV1(BaseModel):
    payer_id: UUID
    payment_gateway: PgpCode = PgpCode.STRIPE
    token: str
    set_default: bool
    is_scanned: bool
    is_active: bool
