from typing import Optional

from pydantic import BaseModel

from app.payin.core.types import LegacyPaymentInfo


class CreatePaymentMethodRequest(BaseModel):
    # TODO: we should enforce payer_id after migration is completed.
    payer_id: Optional[str]
    payment_gateway: str
    token: str
    legacy_payment_info: Optional[LegacyPaymentInfo]


# https://pydantic-docs.helpmanual.io/#self-referencing-models
CreatePaymentMethodRequest.update_forward_refs()
