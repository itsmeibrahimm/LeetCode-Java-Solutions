from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode


class CreatePaymentMethodRequestV0(BaseModel):
    token: str
    country: CountryCode = CountryCode.US
    stripe_customer_id: str
    dd_consumer_id: Optional[
        str
    ]  # optional, stored as legacy information for reference
