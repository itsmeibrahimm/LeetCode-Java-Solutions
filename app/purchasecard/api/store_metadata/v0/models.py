from datetime import datetime

from pydantic import BaseModel

from app.commons.api.models import PaymentResponse


class LinkStoreWithMidRequest(BaseModel):
    store_id: str
    mid: str
    mname: str


class LinkStoreWithMidResponse(PaymentResponse):
    updated_at: datetime
