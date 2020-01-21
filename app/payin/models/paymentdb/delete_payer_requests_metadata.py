from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, String, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class DeletePayerRequestsMetadataTable(TableDefinition):
    name: str = no_init_field("delete_payer_requests_metadata")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    client_request_id: Column = no_init_field(
        Column("client_request_id", UUID(as_uuid=True), unique=True)
    )
    consumer_id: Column = no_init_field(Column("consumer_id", BigInteger))
    country_code: Column = no_init_field(Column("country_code", String))
    email: Column = no_init_field(Column("email", Text))
    status: Column = no_init_field(Column("status", Text))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
