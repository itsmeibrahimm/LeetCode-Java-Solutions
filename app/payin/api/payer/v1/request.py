from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.payer.types import PayerType


class CreatePayerRequest(BaseModel):
    # FIXME: PAY-3773 re-enforce dd_payer_id when the consumer_id constraint in maindb.stripe_card is removed.
    dd_payer_id: str
    payer_type: PayerType
    email: str
    country: CountryCode = CountryCode.US
    description: str


class DefaultPaymentMethod(BaseModel):
    payment_method_id: Optional[UUID]
    dd_stripe_card_id: Optional[
        str
    ]  # first-class support for dd_stripe_card_id in v1 API because we can't backfill all the existing Cx's card objects.


class UpdatePayerRequest(BaseModel):
    default_payment_method: DefaultPaymentMethod
