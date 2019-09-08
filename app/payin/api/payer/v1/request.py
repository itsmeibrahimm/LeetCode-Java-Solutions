from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.payer.types import PayerType
from app.payin.core.types import PaymentMethodIdType


class CreatePayerRequest(BaseModel):
    dd_payer_id: str
    payer_type: PayerType
    email: str
    country: CountryCode = CountryCode.US
    description: str


# https://pydantic-docs.helpmanual.io/#self-referencing-models
CreatePayerRequest.update_forward_refs()


class DefaultPaymentMethod(BaseModel):
    id: str
    payment_method_id_type: Optional[
        PaymentMethodIdType
    ] = PaymentMethodIdType.PAYMENT_METHOD_ID


class UpdatePayerRequest(BaseModel):
    default_payment_method: DefaultPaymentMethod
    country: CountryCode = CountryCode.US


# class UpdatePayerRequest(BaseModel):
#     default_payment_method_id: Optional[str]
#     default_source_id: Optional[str]
#     default_card_id: Optional[str]
#     payer_id_type: Optional[str]
#     payer_type: Optional[str]


# https://pydantic-docs.helpmanual.io/#self-referencing-models
UpdatePayerRequest.update_forward_refs()
