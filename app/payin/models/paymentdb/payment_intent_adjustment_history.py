from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PaymentIntentAdjustmentTable(TableDefinition):
    name: str = no_init_field("payment_intents_adjustment_history")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    payer_id: Column = no_init_field(Column("payer_id", Text))
    payment_intent_id: Column = no_init_field(Column("payment_intent_id", Text))
    amount: Column = no_init_field(Column("amount", Integer))
    amount_original: Column = no_init_field(Column("amount_original", Integer))
    amount_delta: Column = no_init_field(Column("amount_delta", Integer))
    currency: Column = no_init_field(Column("currency", String))
    created_at: Column = no_init_field(Column("created_at", DateTime(False)))
