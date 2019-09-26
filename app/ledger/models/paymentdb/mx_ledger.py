from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, BigInteger
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MxLedgerTable(TableDefinition):
    name: str = no_init_field("mx_ledgers")
    id: Column = no_init_field(Column("id", Text, primary_key=True))
    type: Column = no_init_field(Column("type", Text))
    currency: Column = no_init_field(Column("currency", Text))
    state: Column = no_init_field(Column("state", Text))
    balance: Column = no_init_field(Column("balance", BigInteger))
    amount_paid: Column = no_init_field(
        Column("amount_paid", BigInteger)
    )  # amount paid through payout service
    payment_account_id: Column = no_init_field(Column("payment_account_id", Text))
    legacy_transfer_id: Column = no_init_field(Column("legacy_transfer_id", Text))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    submitted_at: Column = no_init_field(Column("submitted_at", DateTime(True)))
    finalized_at: Column = no_init_field(Column("finalized_at", DateTime(True)))
    created_by_employee_id: Column = no_init_field(
        Column("created_by_employee_id", Text)
    )
    submitted_by_employee_id: Column = no_init_field(
        Column("submitted_by_employee_id", Text)
    )
    rolled_to_ledger_id: Column = no_init_field(Column("rolled_to_ledger_id", Text))
