from dataclasses import dataclass

from sqlalchemy import Column, Integer, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class CardAcceptorStoreAssociationTable(TableDefinition):
    name: str = no_init_field("card_acceptor_store_association")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    strength: Column = no_init_field(Column("strength", Integer))
    status: Column = no_init_field(Column("status", Text))
    card_acceptor_id: Column = no_init_field(Column("card_acceptor_id", Integer))
    manually_checked_by_id: Column = no_init_field(
        Column("manually_checked_by_id", Integer)
    )
    store_id: Column = no_init_field(Column("store_id", Integer))
    unique_drivers: Column = no_init_field(Column("unique_drivers", Text))
