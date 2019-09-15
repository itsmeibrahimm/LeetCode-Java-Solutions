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
