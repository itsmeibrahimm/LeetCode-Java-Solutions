from uuid import UUID

from pydantic import BaseModel

from app.commons.utils.types import PaymentProvider


class CreatePaymentMethodRequest(BaseModel):
    # TODO: we should enforce payer_id after migration is completed.
    payer_id: UUID
    payment_gateway: PaymentProvider = PaymentProvider.STRIPE
    token: str
    set_default: bool
    is_scanned: bool
    is_active: bool
