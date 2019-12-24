from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Local(BaseModel):
    stripe_cards: bool
    stripe_charges: bool
    cart_payments: bool


class Stripe(BaseModel):
    customer: bool


class ThirdParty(BaseModel):
    stripe: Stripe


class Summary(BaseModel):
    local: Local
    third_party: ThirdParty


class DeletePayerRequest(BaseModel):
    id: UUID
    request_id: UUID
    consumer_id: Optional[int]
    payer_id: Optional[UUID]
    status: str
    summary: Optional[Summary]
    retry_count: int
    created_at: datetime
    updated_at: datetime
    acknowledged: bool
