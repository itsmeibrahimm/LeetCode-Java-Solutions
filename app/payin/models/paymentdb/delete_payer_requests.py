from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class DeletePayerRequestsTable(TableDefinition):
    name: str = no_init_field("delete_payer_requests")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    request_id: Column = no_init_field(
        Column("request_id", UUID(as_uuid=True), unique=True)
    )
    consumer_id: Column = no_init_field(Column("consumer_id", Integer))
    payer_id: Column = no_init_field(Column("payer_id", UUID(as_uuid=True)))
    status: Column = no_init_field(Column("status", Text))
    summary: Column = no_init_field(Column("summary", JSON))
    retry_count: Column = no_init_field(Column("retry_count", Integer))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    acknowledged: Column = no_init_field(Column("acknowledged", Boolean))
