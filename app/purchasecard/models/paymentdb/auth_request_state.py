from datetime import datetime
from enum import Enum
from uuid import UUID as uuid_UUID
from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class AuthRequestStateTable(TableDefinition):
    name: str = no_init_field("auth_request_state")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    auth_request_id: Column = no_init_field(
        Column("auth_request_id", UUID(as_uuid=True))
    )
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    state: Column = no_init_field(Column("state", Text))
    subtotal: Column = no_init_field(Column("subtotal", Integer))
    subtotal_tax: Column = no_init_field(Column("subtotal_tax", Integer))


# TODO: @jasmine-tea to complete design and review with clement
class AuthRequestStateName(str, Enum):
    ACTIVE_CREATED = "CREATED"
    ACTIVE_UPDATED = "UPDATED"
    CLOSED_REVOKED = "REVOKED"
    CLOSED_EXPIRED = "EXPIRED"
    CLOSED_CONSUMED = "CONSUMED"
    CLOSED_MANUAL = "MANUAL"


class AuthRequestState(DBEntity):
    id: uuid_UUID
    auth_request_id: uuid_UUID
    created_at: datetime
    updated_at: datetime
    state: AuthRequestStateName
    subtotal: int
    subtotal_tax: int
