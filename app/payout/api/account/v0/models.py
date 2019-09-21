from datetime import datetime
from enum import Enum
from typing import List, Optional
import json

from app.commons.api.models import PaymentRequest, PaymentResponse

# Dummy v0 api models copied directly from db domain models. Just to make sure v0 API signature is stable
# even if underlying db model changes, so we don't need to worry about DSJ v0 integration
from app.payout.repository.maindb.model import stripe_managed_account
from app.payout.types import AccountType


class Entity(str, Enum):
    DASHER = "dasher"
    STORE = "store"
    MERCHANT = "merchant"
    OTHER = "other"
    PARTNER = "partner"


class ResolveOutStandingBalanceFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


class PaymentAccount(PaymentResponse):
    id: int
    statement_descriptor: str
    created_at: Optional[datetime]
    account_id: Optional[int]
    account_type: Optional[AccountType]
    entity: Optional[Entity]
    resolve_outstanding_balance_frequency: Optional[ResolveOutStandingBalanceFrequency]
    payout_disabled: Optional[bool]
    charges_enabled: Optional[bool]
    old_account_id: Optional[int]
    upgraded_to_managed_account_at: Optional[datetime]
    is_verified_with_stripe: Optional[bool]
    transfers_enabled: Optional[bool]


class PaymentAccountCreate(PaymentRequest):
    statement_descriptor: str
    account_id: Optional[int]
    account_type: Optional[AccountType]
    entity: Optional[Entity]
    resolve_outstanding_balance_frequency: Optional[ResolveOutStandingBalanceFrequency]
    payout_disabled: Optional[bool]
    charges_enabled: Optional[bool]
    old_account_id: Optional[int]
    upgraded_to_managed_account_at: Optional[datetime]
    is_verified_with_stripe: Optional[bool]
    transfers_enabled: Optional[bool]


class PaymentAccountUpdate(PaymentRequest):
    account_id: Optional[int]
    account_type: Optional[AccountType]
    entity: Optional[Entity]
    resolve_outstanding_balance_frequency: Optional[ResolveOutStandingBalanceFrequency]
    payout_disabled: Optional[bool]
    charges_enabled: Optional[bool]
    old_account_id: Optional[int]
    upgraded_to_managed_account_at: Optional[datetime]
    is_verified_with_stripe: Optional[bool]
    transfers_enabled: Optional[bool]
    statement_descriptor: Optional[str]


class StripeManagedAccount(PaymentResponse):
    id: int
    country_shortname: str
    stripe_id: str
    stripe_last_updated_at: Optional[datetime]
    bank_account_last_updated_at: Optional[datetime]
    fingerprint: Optional[str]
    default_bank_last_four: Optional[str]
    default_bank_name: Optional[str]
    verification_disabled_reason: Optional[str]
    verification_due_by: Optional[datetime]
    verification_fields_needed: Optional[list]

    @classmethod
    def from_db_model(
        cls, internal: stripe_managed_account.StripeManagedAccount
    ) -> "StripeManagedAccount":
        verification_fields_needed: Optional[list] = None
        if internal.verification_fields_needed:
            verification_fields_needed = json.loads(internal.verification_fields_needed)

        return cls(
            **internal.dict(exclude={"verification_fields_needed"}),
            verification_fields_needed=verification_fields_needed
        )


class StripeManagedAccountCreate(PaymentRequest):
    country_shortname: str
    stripe_id: str
    stripe_last_updated_at: Optional[datetime]
    bank_account_last_updated_at: Optional[datetime]
    fingerprint: Optional[str]
    default_bank_last_four: Optional[str]
    default_bank_name: Optional[str]
    verification_disabled_reason: Optional[str]
    verification_due_by: Optional[datetime]
    verification_fields_needed: Optional[List[str]]

    def to_db_model(self) -> stripe_managed_account.StripeManagedAccountCreate:
        internal_data = self.dict(skip_defaults=True)
        if "verification_fields_needed" in internal_data:
            if internal_data["verification_fields_needed"] is not None:
                internal_data["verification_fields_needed"] = json.dumps(
                    self.verification_fields_needed
                )
        return stripe_managed_account.StripeManagedAccountCreate(**internal_data)


class StripeManagedAccountUpdate(PaymentRequest):
    country_shortname: Optional[str]
    stripe_id: Optional[str]
    stripe_last_updated_at: Optional[datetime]
    bank_account_last_updated_at: Optional[datetime]
    fingerprint: Optional[str]
    default_bank_last_four: Optional[str]
    default_bank_name: Optional[str]
    verification_disabled_reason: Optional[str]
    verification_due_by: Optional[datetime]
    verification_fields_needed: Optional[List[str]]

    def to_db_model(self) -> stripe_managed_account.StripeManagedAccountUpdate:
        internal_data = self.dict(skip_defaults=True)
        if "verification_fields_needed" in internal_data:
            if internal_data["verification_fields_needed"] is not None:
                internal_data["verification_fields_needed"] = json.dumps(
                    self.verification_fields_needed
                )
        return stripe_managed_account.StripeManagedAccountUpdate(**internal_data)
