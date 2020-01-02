from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.commons.api.models import PaymentResponse


class StoreInfo(BaseModel):
    store_id: str
    store_city: str
    store_business_name: str


class CreateAuthRequest(BaseModel):
    amount: int
    store_meta: StoreInfo
    delivery_id: str
    delivery_requires_purchase_card: bool
    shift_id: str
    ttl: Optional[int]


# V0 auth_request_id will be delivery_id
class CreateAuthResponse(PaymentResponse):
    delivery_id: str
    created_at: datetime
    updated_at: datetime
