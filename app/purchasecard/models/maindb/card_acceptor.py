from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, Text, Boolean
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class CardAcceptorTable(TableDefinition):
    name: str = no_init_field("card_acceptor")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    mid: Column = no_init_field(Column("mid", Text))
    card_acceptor_name: Column = no_init_field(Column("name", Text))
    city: Column = no_init_field(Column("city", Text))
    zip_code: Column = no_init_field(Column("zip_code", Text))
    state: Column = no_init_field(Column("state", Text))
    is_blacklisted: Column = no_init_field(Column("is_blacklisted", Boolean))
    blacklisted_by_id: Column = no_init_field(Column("blacklisted_by_id", Integer))
    should_be_examined: Column = no_init_field(Column("should_be_examined", Boolean))


class CardAcceptor(DBEntity):
    id: int
    created_at: datetime
    mid: str
    name: str
    city: str
    zip_code: str
    state: str
    is_blacklisted: bool
    blacklisted_by_id: Optional[int]
    should_be_examined: bool
