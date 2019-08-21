from dataclasses import dataclass

from sqlalchemy import BigInteger, Column, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MxScheduledLedgerTable(TableDefinition):
    """
    The start_time and end_time datetime will be in UTC time
    The start_time and end_time represents 00:00:00 in Pacific time, e.g 2018-07-30 07:00:00
    When create weekly payouts, the cutoff time would use start_time and end_time converted to Pacific time for US/CA marketplace.
    """

    name: str = no_init_field("mx_scheduled_ledgers")
    id: Column = no_init_field(Column("id", Text, primary_key=True))
    payment_account_id: Column = no_init_field(Column("payment_account_id", Text))
    interval_type: Column = no_init_field(Column("interval_type", Text))
    start_time: Column = no_init_field(Column("start_time", DateTime(False)))
    end_time: Column = no_init_field(Column("end_time", DateTime(False)))
    ledger_id: Column = no_init_field(Column("ledger_id", Text))
    closed_at: Column = no_init_field(Column("closed_at", BigInteger))
    created_at: Column = no_init_field(Column("created_at", DateTime(False)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(False)))
