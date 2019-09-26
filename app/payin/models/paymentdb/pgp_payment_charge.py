from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PgpPaymentChargeTable(TableDefinition):
    name: str = no_init_field("pgp_payment_charges")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    payment_charge_id: Column = no_init_field(
        Column("payment_charge_id", UUID(as_uuid=True))
    )
    provider: Column = no_init_field(Column("provider", String))
    idempotency_key: Column = no_init_field(Column("idempotency_key", Text))
    status: Column = no_init_field(Column("status", String))
    currency: Column = no_init_field(Column("currency", String))
    amount: Column = no_init_field(Column("amount", Integer))
    amount_refunded: Column = no_init_field(Column("amount_refunded", Integer))
    application_fee_amount: Column = no_init_field(
        Column("application_fee_amount", Integer)
    )
    payout_account_id: Column = no_init_field(Column("payout_account_id", Text))
    resource_id: Column = no_init_field(Column("resource_id", Text))
    intent_resource_id: Column = no_init_field(Column("intent_resource_id", Text))
    invoice_resource_id: Column = no_init_field(Column("invoice_resource_id", Text))
    payment_method_resource_id: Column = no_init_field(
        Column("payment_method_resource_id", Text)
    )
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    captured_at: Column = no_init_field(Column("captured_at", DateTime(True)))
    cancelled_at: Column = no_init_field(Column("cancelled_at", DateTime(True)))
