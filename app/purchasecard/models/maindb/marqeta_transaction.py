from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, Text, Boolean
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MarqetaTransactionTable(TableDefinition):
    name: str = no_init_field("marqeta_transaction")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    token: Column = no_init_field(Column("token", Text))
    amount: Column = no_init_field(Column("amount", Integer))
    swiped_at: Column = no_init_field(Column("swiped_at", DateTime(True)))
    delivery_id: Column = no_init_field(Column("delivery_id", Integer))
    card_acceptor: Column = no_init_field(Column("card_acceptor", Text))
    currency: Column = no_init_field(Column("currency", Text))
    timed_out: Column = no_init_field(Column("timed_out", Boolean))
    shift_delivery_assignment_id: Column = no_init_field(
        Column("shift_delivery_assignment_id", Integer)
    )


class MarqetaTransaction(DBEntity):
    id: int
    token: str
    amount: int
    swiped_at: datetime
    delivery_id: int
    card_acceptor: str
    currency: Optional[str]
    timed_out: Optional[bool]
    shift_delivery_assignment_id: Optional[int]
