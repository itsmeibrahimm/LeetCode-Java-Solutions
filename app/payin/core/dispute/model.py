from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from typing_extensions import final


class StripeDispute(BaseModel):
    id: int
    stripe_dispute_id: str
    disputed_at: datetime
    amount: int
    fee: int
    net: int
    charged_at: datetime
    reason: str
    status: str
    evidence_due_by: datetime
    stripe_card_id: int
    stripe_charge_id: int
    currency: Optional[str] = None
    evidence_submitted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@final
class Dispute(StripeDispute):
    pass


class DisputeList(BaseModel):
    count: int
    has_more: bool  # Currently default to False. Returning all the disputes for a query
    data: List[Dispute]
