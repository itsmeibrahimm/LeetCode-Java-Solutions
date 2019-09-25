from dataclasses import dataclass

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Boolean, JSON
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
    reference_id: Column = no_init_field(Column("reference_id", String))
    reference_type: Column = no_init_field(Column("reference_type", String))
    legacy_consumer_id: Column = no_init_field(Column("legacy_consumer_id", BigInteger))
    amount_original: Column = no_init_field(Column("amount_original", Integer))
    amount_total: Column = no_init_field(Column("amount_total", Integer))
    delay_capture: Column = no_init_field(Column("delay_capture", Boolean))
    client_description: Column = no_init_field(Column("client_description", String))
    metadata: Column = no_init_field(Column("metadata", JSON))
    legacy_stripe_card_id: Column = no_init_field(
        Column("legacy_stripe_card_id", Integer)
    )
    legacy_provider_customer_id: Column = no_init_field(
        Column("legacy_provider_customer_id", String)
    )
    legacy_provider_payment_method_id: Column = no_init_field(
        Column("legacy_provider_payment_method_id", String)
    )
    legacy_provider_card_id: Column = no_init_field(
        Column("legacy_provider_card_id", String)
    )
    created_at: Column = no_init_field(Column("created_at", DateTime(False)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(False)))
    deleted_at: Column = no_init_field(Column("deleted_at", DateTime(False)))
