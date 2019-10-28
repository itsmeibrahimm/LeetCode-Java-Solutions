from dataclasses import dataclass

from sqlalchemy import Column, Integer, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MarqetaCardTable(TableDefinition):
    name: str = no_init_field("marqeta_card")
    token: Column = no_init_field(Column("token", Text, primary_key=True))
    delight_number: Column = no_init_field(Column("delight_number", Integer))
    terminated_at: Column = no_init_field(Column("terminated_at", DateTime(True)))
    last4: Column = no_init_field(Column("last4", Text))
