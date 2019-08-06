from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from typing_extensions import final


@final
@dataclass(frozen=True)
class Card:
    last4: str
    exp_year: str
    exp_month: str
    fingerprint: str
    active: bool
    country: Optional[str]
    brand: Optional[str]
    payment_provider_card_id: Optional[str] = None


@final
@dataclass(frozen=True)
class PaymentMethod:
    id: str
    payment_provider: str
    card: Card
    payer_id: Optional[str]
    type: Optional[str]
    dd_consumer_id: Optional[str] = None
    payment_provider_customer_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
