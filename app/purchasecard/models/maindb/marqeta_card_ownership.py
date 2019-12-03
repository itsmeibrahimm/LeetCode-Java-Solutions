from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MarqetaCardOwnershipTable(TableDefinition):
    name: str = no_init_field("marqeta_card_ownership")
    id: Column = no_init_field(Column("id", Integer, primary_key=True, nullable=False))
    created_at: Column = no_init_field(
        Column("created_at", DateTime(True), nullable=False)
    )
    ended_at: Column = no_init_field(Column("ended_at", DateTime(True)))
    card_id: Column = no_init_field(Column("card_id", Text, nullable=False))
    dasher_id: Column = no_init_field(Column("dasher_id", Integer, nullable=False))


class MarqetaCardOwnership(DBEntity):
    id: int
    created_at: datetime
    ended_at: Optional[datetime]
    card_id: str
    dasher_id: int
