from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PaymentIntentTable(TableDefinition):
    name: str = no_init_field("payment_intents")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    cart_payment_id: Column = no_init_field(Column("cart_payment_id", Text))
    idempotency_key: Column = no_init_field(Column("idempotency_key", Text))
    amount_initiated: Column = no_init_field(Column("amount_initiated", Integer))
    amount: Column = no_init_field(Column("amount", Integer))
    amount_capturable: Column = no_init_field(Column("amount_capturable", Integer))
    amount_received: Column = no_init_field(Column("amount_received", Integer))
    application_fee_amount: Column = no_init_field(
        Column("application_fee_amount", Integer)
    )
    capture_method: Column = no_init_field(Column("capture_method", String))
    confirmation_method: Column = no_init_field(Column("confirmation_method", String))
    country: Column = no_init_field(Column("country", String))
    currency: Column = no_init_field(Column("currency", String))
    status: Column = no_init_field(Column("status", String))
    statement_descriptor: Column = no_init_field(Column("statement_descriptor", String))
    payment_method_id: Column = no_init_field(
        Column("payment_method_id", UUID(as_uuid=True))
    )
    metadata: Column = no_init_field(Column("metadata", JSON))
    created_at: Column = no_init_field(Column("created_at", DateTime(False)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(False)))
    captured_at: Column = no_init_field(Column("captured_at", DateTime(False)))
    cancelled_at: Column = no_init_field(Column("cancelled_at", DateTime(False)))
    capture_after: Column = no_init_field(Column("capture_after", DateTime(False)))
