from dataclasses import dataclass

from sqlalchemy import Column, Integer, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StoreMastercardDataTable(TableDefinition):
    name: str = no_init_field("store_mastercard_data")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    mid: Column = no_init_field(Column("mid", Text))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    store_id: Column = no_init_field(Column("store_id", Integer))
    mname: Column = no_init_field(Column("mname", Text))
