from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StoreMastercardDataTable(TableDefinition):
    name: str = no_init_field("store_mastercard_data")
    id: Column = no_init_field(Column("id", Integer, primary_key=True, nullable=False))
    mid: Column = no_init_field(Column("mid", Text, nullable=False))
    updated_at: Column = no_init_field(
        Column("updated_at", DateTime(timezone=True), nullable=False)
    )
    store_id: Column = no_init_field(Column("store_id", Integer, nullable=False))
    mname: Column = no_init_field(Column("mname", Text))


class StoreMastercardData(DBEntity):
    id: int  # server default generated
    updated_at: datetime
    mid: str
    store_id: int
    mname: Optional[str]
