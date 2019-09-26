from dataclasses import dataclass

from sqlalchemy import Column, Text, DateTime, Integer
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StripeDisputeTable(TableDefinition):
    name: str = no_init_field("stripe_dispute")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    stripe_dispute_id: str = no_init_field(Column("stripe_dispute_id", Text))
    disputed_at: Column = no_init_field(Column("disputed_at", DateTime(True)))
    amount: Column = no_init_field(Column("amount", Integer))
    fee: Column = no_init_field(Column("fee", Integer))
    net: Column = no_init_field(Column("net", Integer))
    currency: Column = no_init_field(Column("currency", Text))
    charged_at: Column = no_init_field(Column("charged_at", DateTime(True)))
    reason: Column = no_init_field(Column("reason", Text))
    status: Column = no_init_field(Column("status", Text))
    evidence_due_by: Column = no_init_field(Column("evidence_due_by", DateTime(True)))
    evidence_submitted_at: Column = no_init_field(
        Column("evidence_submitted_at", DateTime(True))
    )
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    stripe_card_id: Column = no_init_field(Column("stripe_card_id", Integer))
    stripe_charge_id: Column = no_init_field(Column("stripe_charge_id", Integer))
