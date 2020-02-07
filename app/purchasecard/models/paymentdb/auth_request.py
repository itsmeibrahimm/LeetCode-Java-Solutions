from uuid import UUID as uuid_UUID
from dataclasses import dataclass
from typing import Optional, Dict, Any

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final
from datetime import datetime

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class AuthRequestTable(TableDefinition):
    name: str = no_init_field("auth_request")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    shift_id: Column = no_init_field(Column("shift_id", Text))
    delivery_id: Column = no_init_field(Column("delivery_id", Text))
    dasher_id: Column = no_init_field(Column("dasher_id", Text))
    external_purchasecard_user_token: Column = no_init_field(
        Column("external_purchasecard_user_token", Text)
    )
    store_id: Column = no_init_field(Column("store_id", Text))
    store_city: Column = no_init_field(Column("store_city", Text))
    store_business_name: Column = no_init_field(Column("store_business_name", Text))
    current_state: Column = no_init_field(Column("current_state", Text))
    expire_sec: Column = no_init_field(Column("expire_sec", Integer))


class AuthRequest(DBEntity):
    id: uuid_UUID
    created_at: datetime
    updated_at: datetime
    shift_id: str
    delivery_id: str
    external_purchasecard_user_token: str
    store_id: str
    store_city: str
    store_business_name: str
    current_state: str
    expire_sec: Optional[int]


class LegacyAuthRequest(BaseModel):
    id: uuid_UUID
    created_at: datetime
    updated_at: datetime
    shift_id: int
    delivery_id: int
    dasher_id: int
    external_purchasecard_user_token: str
    store_id: int
    store_city: str
    store_business_name: str
    current_state: str
    expire_sec: Optional[int]

    @classmethod
    def to_legacy_auth_request(cls, db_entity_dict: Dict[Any, Any]):
        return cls(**db_entity_dict)
