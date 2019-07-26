from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from typing_extensions import final

from app.commons.types import CountryCode


@final
@dataclass(frozen=True)
class PayoutAccount:
    statement_descriptor: str
    id: Optional[int] = None
    account_type: Optional[str] = None
    account_id: Optional[int] = None
    entity: Optional[str] = None
    old_account_id: Optional[int] = None
    upgraded_to_managed_account_at: Optional[datetime] = None
    is_verified_with_stripe: bool = False
    transfers_enabled: bool = False
    charges_enabled: bool = False
    created_at: Optional[datetime] = None
    payout_disabled: Optional[bool] = None
    resolve_outstanding_balance_frequency: Optional[str] = None


@final
@dataclass(frozen=True)
class StripeManagedAccount:
    stripe_id: str
    country_short_name: CountryCode
    id: Optional[int] = None
    stripe_last_updated_at: Optional[datetime] = None
    bank_account_last_updated_at: Optional[datetime] = None
    fingerprint: Optional[str] = None
    default_bank_last_four: Optional[str] = None
    default_bank_name: Optional[str] = None
    verification_disabled_reason: Optional[str] = None
    verification_due_by: Optional[datetime] = None
    verification_fields_needed: Optional[str] = None
