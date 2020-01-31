from dataclasses import dataclass

from sqlalchemy import Column, Integer, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PartialConsumerTable(TableDefinition):
    """
    Partial columns of maindb consumer table that are only needed for migration purpose.
    """

    name: str = no_init_field("consumer")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    stripe_id: Column = no_init_field(Column("stripe_id", Text))
    stripe_country_id: Column = no_init_field(Column("stripe_country_id", Integer))
