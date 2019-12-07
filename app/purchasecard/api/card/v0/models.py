"""
API Request/Response Models
"""
from datetime import datetime
from typing import Optional

from app.commons.api.models import PaymentRequest, PaymentResponse


class AssociateMarqetaCardRequest(PaymentRequest):
    delight_number: int
    last4: str
    is_dispatcher: Optional[bool]
    dasher_id: int
    user_token: str


class AssociateMarqetaCardResponse(PaymentResponse):
    old_card_relinquished: bool
    num_prev_owners: int


class UnassociateMarqetaCardRequest(PaymentRequest):
    dasher_id: int


class UnassociateMarqetaCardResponse(PaymentRequest):
    token: str


class GetMarqetaCardRequest(PaymentRequest):
    dasher_id: int


class GetMarqetaCardResponse(PaymentResponse):
    token: str
    delight_number: int
    terminated_at: Optional[datetime]
    last4: str
