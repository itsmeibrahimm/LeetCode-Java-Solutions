from typing import Optional

from pydantic import BaseModel

from app.commons.utils.types import PaymentProvider
from app.payin.core.types import LegacyPaymentMethodInfo


class CreatePaymentMethodRequest(BaseModel):
    # TODO: we should enforce payer_id after migration is completed.
    payer_id: Optional[str]
    payment_gateway: PaymentProvider = PaymentProvider.STRIPE
    token: str
    legacy_payment_info: Optional[LegacyPaymentMethodInfo]


# https://pydantic-docs.helpmanual.io/#self-referencing-models
CreatePaymentMethodRequest.update_forward_refs()
