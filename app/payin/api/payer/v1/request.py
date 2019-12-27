from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.types import PayerReferenceIdType


class CreatePayerRequest(BaseModel):
    payer_reference_id: str
    payer_reference_id_type: PayerReferenceIdType
    email: str
    country: CountryCode = CountryCode.US
    description: str


class DefaultPaymentMethodV1(BaseModel):
    payment_method_id: Optional[UUID]
    dd_stripe_card_id: Optional[
        str
    ]  # first-class support for dd_stripe_card_id in v1 API because we can't backfill all the existing Cx's card objects.


class UpdatePayerRequestV1(BaseModel):
    default_payment_method: DefaultPaymentMethodV1
