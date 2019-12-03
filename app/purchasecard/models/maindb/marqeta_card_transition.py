from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MarqetaCardTransitionTable(TableDefinition):
    name: str = no_init_field("marqeta_card_transition")
    id: Column = no_init_field(Column("id", Integer, primary_key=True, nullable=False))
    created_at: Column = no_init_field(
        Column("created_at", DateTime(True), nullable=False)
    )
    succeeded_at: Column = no_init_field(Column("succeeded_at", DateTime(True)))
    aborted_at: Column = no_init_field(Column("aborted_at", DateTime(True)))
    desired_state: Column = no_init_field(Column("desired_state", Text, nullable=False))
    card_id: Column = no_init_field(Column("card_id", Text, nullable=False))
    shift_id: Column = no_init_field(Column("shift_id", Integer))


class TransitionState(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class MarqetaCardTransition(DBEntity):
    id: int
    created_at: datetime
    succeeded_at: Optional[datetime]
    aborted_at: Optional[datetime]
    desired_state: TransitionState
    card_id: str
    shift_id: Optional[int]
