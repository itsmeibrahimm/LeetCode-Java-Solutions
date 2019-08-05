from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from typing_extensions import final


@final
@dataclass(frozen=True)
class Card:
    country: str
    last4: str
    exp_year: str
    exp_month: str
    fingerprint: str
    active: bool
    brand: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]


@final
@dataclass(frozen=True)
class PaymentMethod:
    id: str
    payer_id: str
    dd_consumer_id: Optional[str]
    payment_provider_customer_id: Optional[str]
    payment_provider: str
    type: str
    card: Card
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]
