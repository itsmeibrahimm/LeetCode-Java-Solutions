from dataclasses import dataclass

from sqlalchemy import Column, Integer, Text
from typing_extensions import final

from app.commons.database.table import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StripeCustomerTable(TableDefinition):
    name: str = no_init_field("stripe_customer")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    stripe_id: Column = no_init_field(Column("stripe_id", Text))
    country_shortname: Column = no_init_field(Column("country_shortname", Integer))
    owner_type: Column = no_init_field(Column("owner_type", Text))
    owner_id: Column = no_init_field(Column("owner_id", Integer))
    default_card: Column = no_init_field(Column("default_card", Text))
    default_source: Column = no_init_field(Column("default_source", Text))
