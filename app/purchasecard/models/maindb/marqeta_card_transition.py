from dataclasses import dataclass

from sqlalchemy import Column, Integer, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MarqetaCardTransitionTable(TableDefinition):
    name: str = no_init_field("marqeta_card_transition")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    succeeded_at: Column = no_init_field(Column("succeeded_at", DateTime(True)))
    aborted_at: Column = no_init_field(Column("aborted_at", DateTime(True)))
    desired_state: Column = no_init_field(Column("desired_state", Text))
    card_id: Column = no_init_field(Column("card_id", Text))
    shift_id: Column = no_init_field(Column("shift_id", Integer))
