from pydantic import BaseModel

from app.commons.types import CountryCode


class CreatePaymentMethodRequestV0(BaseModel):
    token: str
    country: CountryCode = CountryCode.US
    stripe_customer_id: str
    dd_consumer_id: str  # required field in order to populate MainDB.stripe_card.consumer_id
