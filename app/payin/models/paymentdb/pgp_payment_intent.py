from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PgpPaymentIntentTable(TableDefinition):
    name: str = no_init_field("pgp_payment_intents")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    payment_intent_id: Column = no_init_field(
        Column("payment_intent_id", UUID(as_uuid=True))
    )
    idempotency_key: Column = no_init_field(Column("idempotency_key", Text))
    pgp_code: Column = no_init_field(Column("pgp_code", Text))
    resource_id: Column = no_init_field(Column("resource_id", Text))
    invoice_resource_id: Column = no_init_field(Column("invoice_resource_id", Text))
    charge_resource_id: Column = no_init_field(Column("charge_resource_id", Text))
    payment_method_resource_id: Column = no_init_field(
        Column("payment_method_resource_id", Text)
    )
    customer_resource_id: Column = no_init_field(Column("customer_resource_id", Text))
    currency: Column = no_init_field(Column("currency", Text))
    amount: Column = no_init_field(Column("amount", Integer))
    amount_capturable: Column = no_init_field(Column("amount_capturable", Integer))
    amount_received: Column = no_init_field(Column("amount_received", Integer))
    application_fee_amount: Column = no_init_field(
        Column("application_fee_amount", Integer)
    )
    capture_method: Column = no_init_field(Column("capture_method", Text))
    payout_account_id: Column = no_init_field(Column("payout_account_id", Text))
    status: Column = no_init_field(Column("status", Text))
    statement_descriptor: Column = no_init_field(Column("statement_descriptor", Text))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    captured_at: Column = no_init_field(Column("captured_at", DateTime(True)))
    cancelled_at: Column = no_init_field(Column("cancelled_at", DateTime(True)))
