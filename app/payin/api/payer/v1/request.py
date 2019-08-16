from typing import Optional

from pydantic import BaseModel

from app.payin.core.payer.types import PayerType


class CreatePayerRequest(BaseModel):
    dd_payer_id: str
    payer_type: PayerType
    email: str
    country: str
    description: str


# https://pydantic-docs.helpmanual.io/#self-referencing-models
CreatePayerRequest.update_forward_refs()


class DefaultPaymentMethod(BaseModel):
    id: str
    payment_method_id_type: Optional[str]


class UpdatePayerRequest(BaseModel):
    default_payment_method: DefaultPaymentMethod


# class UpdatePayerRequest(BaseModel):
#     default_payment_method_id: Optional[str]
#     default_source_id: Optional[str]
#     default_card_id: Optional[str]
#     payer_id_type: Optional[str]
#     payer_type: Optional[str]


# https://pydantic-docs.helpmanual.io/#self-referencing-models
UpdatePayerRequest.update_forward_refs()
