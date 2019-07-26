from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Integer, Text
from typing_extensions import final

from app.commons.database.table import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StripeManagedAccountTable(TableDefinition):
    name: str = no_init_field("stripe_managed_account")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
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
