from dataclasses import dataclass

from sqlalchemy import Column, Integer, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class FailedConsumerTable(TableDefinition):
    """
    Table to track failed consumer record with only necessary info
    during maindb -> payment db payer data migration.
    This is same as PartialConsumerTable
    """

    name: str = no_init_field("failed_consumer")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    stripe_id: Column = no_init_field(Column("stripe_id", Text))
    stripe_country_id: Column = no_init_field(Column("stripe_country_id", Integer))


@final
@dataclass(frozen=True)
class ConsumerBackfillTrackingTable(TableDefinition):
    """
    A simple tracking table which should always have only one row to
    indicate last succeeded consumer id record.
    """

    name: str = no_init_field("consumer_backfill_tracking")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    consumer_id: Column = no_init_field(Column("consumer_id", Integer))
