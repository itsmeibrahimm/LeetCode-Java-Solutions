from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Column, Integer, DateTime
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class DeliveryFundingTable(TableDefinition):
    name: str = no_init_field("delivery_funding")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    amount: Column = no_init_field(Column("amount", Integer))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    created_by_id: Column = no_init_field(Column("created_by_id", Integer))
    delivery_id: Column = no_init_field(Column("delivery_id", Integer))


class DeliveryFunding(DBEntity):
    id: int
    amount: int
    created_at: datetime
    created_by_id: int
    delivery_id: int
