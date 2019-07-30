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


class UpdatePayerRequest(BaseModel):
    default_payment_method_id: str


# https://pydantic-docs.helpmanual.io/#self-referencing-models
UpdatePayerRequest.update_forward_refs()
