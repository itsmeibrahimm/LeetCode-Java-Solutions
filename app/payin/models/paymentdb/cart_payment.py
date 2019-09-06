from dataclasses import dataclass

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class CartPaymentTable(TableDefinition):
    name: str = no_init_field("cart_payments")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    payer_id: Column = no_init_field(Column("payer_id", UUID(as_uuid=True)))
    type: Column = no_init_field(Column("type", String))
    reference_id: Column = no_init_field(Column("reference_id", BigInteger))
    reference_ct_id: Column = no_init_field(Column("reference_ct_id", BigInteger))
    legacy_charge_id: Column = no_init_field(Column("legacy_charge_id", BigInteger))
    legacy_consumer_id: Column = no_init_field(Column("legacy_consumer_id", BigInteger))
    amount_original: Column = no_init_field(Column("amount_original", Integer))
    amount_total: Column = no_init_field(Column("amount_total", Integer))
    delay_capture: Column = no_init_field(Column("delay_capture", Boolean))
    client_description: Column = no_init_field(Column("client_description", String))
    created_at: Column = no_init_field(Column("created_at", DateTime(False)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(False)))
    deleted_at: Column = no_init_field(Column("deleted_at", DateTime(False)))
