from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class RefundTable(TableDefinition):
    name: str = no_init_field("refunds")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    payment_intent_id: Column = no_init_field(
        Column("payment_intent_id", UUID(as_uuid=True))
    )
    idempotency_key: Column = no_init_field(Column("idempotency_key", Text))
    status: Column = no_init_field(Column("status", Text))
    amount: Column = no_init_field(Column("amount", Integer))
    reason: Column = no_init_field(Column("reason", Text))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
