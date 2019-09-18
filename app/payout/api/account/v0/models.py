from datetime import datetime
from typing import Optional
import json

from app.commons.api.models import PaymentRequest, PaymentResponse

# Dummy v0 api models copied directly from db domain models. Just to make sure v0 API signature is stable
# even if underlying db model changes, so we don't need to worry about DSJ v0 integration
from app.commons.utils.types import (
    NullableString,
    NullableInteger,
    NullableBoolean,
    NullableDatetime,
    NullableAccount,
    Nullable,
    NullableList,
)
from app.payout.repository.maindb.model import stripe_managed_account
from app.payout.types import AccountType


class PaymentAccount(PaymentResponse):
    id: int
    statement_descriptor: str
    created_at: Optional[datetime]
    account_id: Optional[int]
    account_type: Optional[AccountType]
    entity: Optional[str]
    resolve_outstanding_balance_frequency: Optional[str]
    payout_disabled: Optional[bool]
    charges_enabled: Optional[bool]
    old_account_id: Optional[int]
    upgraded_to_managed_account_at: Optional[datetime]
    is_verified_with_stripe: Optional[bool]
    transfers_enabled: Optional[bool]


class PaymentAccountCreate(PaymentRequest):
    statement_descriptor: str
    account_id: Optional[NullableInteger]
    account_type: Optional[NullableAccount]
    entity: Optional[NullableString]
    resolve_outstanding_balance_frequency: Optional[NullableString]
    payout_disabled: Optional[NullableBoolean]
    charges_enabled: Optional[NullableBoolean]
    old_account_id: Optional[NullableInteger]
    upgraded_to_managed_account_at: Optional[NullableDatetime]
    is_verified_with_stripe: Optional[NullableBoolean]
    transfers_enabled: Optional[NullableBoolean]


class PaymentAccountUpdate(PaymentRequest):
    account_id: Optional[NullableInteger]
    account_type: Optional[NullableAccount]
    entity: Optional[NullableString]
    resolve_outstanding_balance_frequency: Optional[NullableString]
    payout_disabled: Optional[NullableBoolean]
    charges_enabled: Optional[NullableBoolean]
    old_account_id: Optional[NullableInteger]
    upgraded_to_managed_account_at: Optional[NullableDatetime]
    is_verified_with_stripe: Optional[NullableBoolean]
    transfers_enabled: Optional[NullableBoolean]
    # leave statement_descriptor as Optional[str] since it's not null in db
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
    stripe_last_updated_at: Optional[NullableDatetime]
    bank_account_last_updated_at: Optional[NullableDatetime]
    fingerprint: Optional[NullableString]
    default_bank_last_four: Optional[NullableString]
    default_bank_name: Optional[NullableString]
    verification_disabled_reason: Optional[NullableString]
    verification_due_by: Optional[NullableDatetime]
    verification_fields_needed: Optional[NullableList]

    def to_db_model(self) -> stripe_managed_account.StripeManagedAccountCreate:
        verification_fields_needed = None
        if (
            self.verification_fields_needed
            and self.verification_fields_needed.value is not None
        ):
            verification_fields_needed = json.dumps(
                self.verification_fields_needed.value
            )
        return stripe_managed_account.StripeManagedAccountCreate(
            **{
                k: v.value if issubclass(type(v), Nullable) else v
                for k, v in self.dict(
                    exclude={"verification_fields_needed"}, skip_defaults=True
                ).items()
            },
            verification_fields_needed=verification_fields_needed
        )


class StripeManagedAccountUpdate(PaymentRequest):
    # leave country_shortname and stripe_id as Optional[str] since they're not null in db
    country_shortname: Optional[str]
    stripe_id: Optional[str]
    stripe_last_updated_at: Optional[NullableDatetime]
    bank_account_last_updated_at: Optional[NullableDatetime]
    fingerprint: Optional[NullableString]
    default_bank_last_four: Optional[NullableString]
    default_bank_name: Optional[NullableString]
    verification_disabled_reason: Optional[NullableString]
    verification_due_by: Optional[NullableDatetime]
    verification_fields_needed: Optional[NullableList]

    def to_db_model(self) -> stripe_managed_account.StripeManagedAccountUpdate:
        internal_data = {
            k: v.value if issubclass(type(v), Nullable) else v
            for k, v in self.dict(
                exclude={"verification_fields_needed"}, skip_defaults=True
            ).items()
        }

        if self.verification_fields_needed and issubclass(
            type(self.verification_fields_needed), Nullable
        ):
            if self.verification_fields_needed.value is not None:
                internal_data["verification_fields_needed"] = json.dumps(
                    self.verification_fields_needed.value
                )
            else:
                internal_data["verification_fields_needed"] = None

        return stripe_managed_account.StripeManagedAccountUpdate(**internal_data)
