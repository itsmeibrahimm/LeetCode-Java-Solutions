from dataclasses import dataclass

from sqlalchemy import Boolean, Column, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PgpCustomerTable(TableDefinition):
    name: str = no_init_field("pgp_customers")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    legacy_id: Column = no_init_field(Column("legacy_id", BigInteger))
    pgp_code: Column = no_init_field(Column("pgp_code", Text))
    pgp_resource_id: Column = no_init_field(Column("pgp_resource_id", Text))
    country: Column = no_init_field(Column("country", Text))
    is_primary: Column = no_init_field(Column("is_primary", Boolean))
    payer_id: Column = no_init_field(
        Column("payer_id", UUID(as_uuid=True), ForeignKey("payer.id"))
    )
    currency: Column = no_init_field(Column("currency", Text))
    balance: Column = no_init_field(Column("balance", BigInteger))
    default_payment_method_id: Column = no_init_field(
        Column("default_payment_method_id", Text)
    )
    legacy_default_source_id: Column = no_init_field(
        Column("legacy_default_source_id", Text)
    )
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
