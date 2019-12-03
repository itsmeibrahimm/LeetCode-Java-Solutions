from typing import Optional

from pydantic import BaseModel


class InternalAssociateCardResponse(BaseModel):
    old_card_relinquished: Optional[bool]
    num_prev_owners: Optional[int]
