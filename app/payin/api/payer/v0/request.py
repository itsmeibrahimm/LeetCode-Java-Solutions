from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode


class DefaultPaymentMethodV0(BaseModel):
    dd_stripe_card_id: Optional[str]
    dd_payment_method_id: Optional[str]


class UpdatePayerRequestV0(BaseModel):
    default_payment_method: DefaultPaymentMethodV0
    country: CountryCode = CountryCode.US
