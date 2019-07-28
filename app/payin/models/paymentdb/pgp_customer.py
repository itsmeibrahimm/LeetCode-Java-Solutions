from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, BigInteger, ForeignKey
from typing_extensions import final

from app.commons.database.table import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PgpCustomerTable(TableDefinition):
    name: str = no_init_field("pgp_customer")
    id: Column = no_init_field(Column("id", Text, primary_key=True))
    legacy_id: Column = no_init_field(Column("legacy_id", BigInteger))
    pgp_code: Column = no_init_field(Column("pgp_code", Text))
    pgp_resource_id: Column = no_init_field(Column("pgp_resource_id", Text))
    payer_id: Column = no_init_field(Column("payer_id", Text, ForeignKey("payer.id")))
    currency: Column = no_init_field(Column("currency", Text))
    account_balance: Column = no_init_field(Column("account_balance", BigInteger))
    default_payment_method: Column = no_init_field(
        Column("default_payment_method", Text)
    )
    legacy_default_card: Column = no_init_field(Column("legacy_default_card", Text))
    legacy_default_source: Column = no_init_field(Column("legacy_default_source", Text))
    created_at: Column = no_init_field(Column("created_at", DateTime(False)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(False)))
