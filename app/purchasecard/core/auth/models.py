from datetime import datetime

from pydantic import BaseModel


class InternalStoreInfo(BaseModel):
    store_id: str
    store_city: str
    store_business_name: str


class InternalCreateAuthResponse(BaseModel):
    delivery_id: str
    created_at: datetime
    updated_at: datetime


class UpdatedAuthorization(BaseModel):
    updated_at: datetime
    state: str
    delivery_id: str
    shift_id: str


class ClosedAuthorization(BaseModel):
    num_success: int
