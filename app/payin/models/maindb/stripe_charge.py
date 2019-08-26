from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, Integer, JSON
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StripeChargeTable(TableDefinition):
    name: str = no_init_field("stripe_charge")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))

    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    refunded_at: Column = no_init_field(Column("refunded_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    stripe_id: Column = no_init_field(Column("stripe_id", Text))
    card_id: Column = no_init_field(Column("card_id", Integer))
    charge_id: Column = no_init_field(Column("charge_id", Integer))

    amount: Column = no_init_field(Column("amount", Integer))
    amount_refunded: Column = no_init_field(Column("amount_refunded", Integer))

    currency: Column = no_init_field(Column("currency", Text))
    status: Column = no_init_field(Column("status", Text))
    error_reason: Column = no_init_field(Column("error_reason", Text))

    additional_payment_info: Column = no_init_field(
        Column("additional_payment_info", JSON)
    )
    description: Column = no_init_field(Column("description", Text))

    idempotency_key: Column = no_init_field(Column("idempotency_key", Text))
