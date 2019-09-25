from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.payer.types import PayerType


class CreatePaymentMethodRequestV0(BaseModel):
    token: str
    country: CountryCode
    stripe_customer_id: str
    payer_type: PayerType
    dd_consumer_id: Optional[
        str
    ]  # required if PayerType is "marketplace" in order to populate MainDB.stripe_card.consumer_id
    dd_stripe_customer_id: Optional[
        str
    ]  # required if PayerType is not "marketplace" in order to populate MainDB.stripe_card.stripe_customer_id
    set_default: Optional[bool] = False
    is_scanned: Optional[bool] = False
