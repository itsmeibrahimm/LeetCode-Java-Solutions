from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.payer.types import PayerType


class DefaultPaymentMethodV0(BaseModel):
    dd_stripe_card_id: str


class UpdatePayerRequestV0(BaseModel):
    default_payment_method: DefaultPaymentMethodV0
    country: CountryCode
    payer_type: Optional[PayerType]
