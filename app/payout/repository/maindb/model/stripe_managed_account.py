from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, Text, text
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StripeManagedAccountTable(TableDefinition):
    name: str = no_init_field("stripe_managed_account")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text("nextval('stripe_managed_account_id_seq'::regclass)"),
        )
    )
    stripe_id: Column = no_init_field(
        Column("stripe_id", Text, nullable=False, index=True)
    )
    country_short_name: Column = no_init_field(
        Column("country_shortname", Text, nullable=False)
    )
    stripe_last_updated_at: Column = no_init_field(
        Column("stripe_last_updated_at", DateTime(True))
    )
    bank_account_last_updated_at: Column = no_init_field(
        Column("bank_account_last_updated_at", DateTime(True))
    )
    fingerprint: Column = no_init_field(Column("fingerprint", Text))
    default_bank_last_four: Column = no_init_field(
        Column("default_bank_last_four", Text)
    )
    default_bank_name: Column = no_init_field(Column("default_bank_name", Text))
    verification_disabled_reason: Column = no_init_field(
        Column("verification_disabled_reason", Text)
    )
    verification_due_by: Column = no_init_field(
        Column("verification_due_by", DateTime(True))
    )
    verification_fields_needed: Column = no_init_field(
        Column("verification_fields_needed", Text)
    )


class _StripeManagedAccountPartial(DBEntity):
    stripe_last_updated_at: Optional[datetime]
    bank_account_last_updated_at: Optional[datetime]
    fingerprint: Optional[str]
    default_bank_last_four: Optional[str]
    default_bank_name: Optional[str]
    verification_disabled_reason: Optional[str]
    verification_due_by: Optional[datetime]
    verification_fields_needed: Optional[str]


class StripeManagedAccount(_StripeManagedAccountPartial):
    id: int  # server default generated

    country_shortname: str
    stripe_id: str


class StripeManagedAccountCreate(_StripeManagedAccountPartial):
    country_shortname: str
    stripe_id: str


class StripeManagedAccountUpdate(_StripeManagedAccountPartial):
    country_shortname: Optional[str]
    stripe_id: Optional[str]
