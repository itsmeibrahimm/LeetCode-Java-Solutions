from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from typing_extensions import final


@dataclass(frozen=True)
class StripeDispute:
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
