from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, BigInteger, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PayerTable(TableDefinition):
    name: str = no_init_field("payers")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    payer_type: Column = no_init_field(Column("payer_type", Text))
    dd_payer_id: Column = no_init_field(Column("dd_payer_id", Text))
    legacy_stripe_customer_id: Column = no_init_field(
        Column("legacy_stripe_customer_id", Text)
    )
    country: Column = no_init_field(Column("country", Text))
    balance: Column = no_init_field(Column("balance", BigInteger))
    description: Column = no_init_field(Column("description", Text))
    metadata: Column = no_init_field(Column("metadata", JSON))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    deleted_at: Column = no_init_field(Column("deleted_at", DateTime(True)))
    default_payment_method_id: Column = no_init_field(
        Column("default_payment_method_id", UUID(as_uuid=True))
    )
    legacy_default_dd_stripe_card_id: Column = no_init_field(
        Column("legacy_default_dd_stripe_card_id", Integer)
    )
