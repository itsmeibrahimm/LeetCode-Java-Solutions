from typing import Optional

from pydantic import BaseModel


class CreateExemptionRequest(BaseModel):
    creator_id: str
    delivery_id: str
    swipe_amount: int
    dasher_id: Optional[str] = None
    mid: Optional[str] = None
    declined_amount: Optional[int] = None
