from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class InternalAssociateCardResponse(BaseModel):
    old_card_relinquished: Optional[bool]
    num_prev_owners: Optional[int]


class InternalUnassociateCardResponse(BaseModel):
    token: str


class InternalGetMarqetaCardResponse(BaseModel):
    token: str
    delight_number: int
    terminated_at: Optional[datetime]
    last4: str
