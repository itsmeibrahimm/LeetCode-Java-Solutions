from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.payer.types import PayerType


class CreatePaymentMethodRequestV0(BaseModel):
    token: str
    country: CountryCode
    stripe_customer_id: str
    # FIXME: can't enforce payer_type for Drive. This is for lazy creation use and will revisit to see if we can
    # do lazy creation without client input before removing it.
    payer_type: Optional[PayerType]
    set_default: bool
    is_scanned: bool
    is_active: bool
    dd_consumer_id: Optional[
        str
    ]  # required if PayerType is "marketplace" in order to populate MainDB.stripe_card.consumer_id
    dd_stripe_customer_id: Optional[
        str
    ]  # required if PayerType is not "marketplace" in order to populate MainDB.stripe_card.stripe_customer_id
