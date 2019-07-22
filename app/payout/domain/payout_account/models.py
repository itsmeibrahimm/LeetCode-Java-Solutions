from datetime import datetime
from typing import Optional

import attr
from typing_extensions import final


@final
@attr.s(auto_attribs=True, frozen=True)
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
