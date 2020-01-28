from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MarqetaTransactionEventTable(TableDefinition):
    name: str = no_init_field("marqeta_transaction_event")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    token: Column = no_init_field(Column("token", Text))
    amount: Column = no_init_field(Column("amount", Integer))
    transaction_type: Column = no_init_field(Column("transaction_type", Text))
    metadata: Column = no_init_field(Column("metadata", Text))
    ownership_id: Column = no_init_field(Column("ownership_id", Integer))
    shift_id: Column = no_init_field(Column("shift_id", Integer))
    raw_type: Column = no_init_field(Column("raw_type", Text))
    card_acceptor_id: Column = no_init_field(Column("card_acceptor_id", Integer))


class MarqetaTransactionEvent(DBEntity):
    id: int
    created_at: datetime
    token: str
    amount: int
    transaction_type: str
    metadata: str
    ownership_id: int
    shift_id: Optional[int]
    raw_type: str
    card_acceptor_id: Optional[int]
