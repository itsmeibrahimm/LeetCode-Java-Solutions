from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Integer, Text, JSON
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MxTransactionTable(TableDefinition):
    name: str = no_init_field("mx_transaction")
    id: Column = no_init_field(Column("id", Text, primary_key=True))
    payment_account_id: Column = no_init_field(Column("payment_account_id", Text))
    amount: Column = no_init_field(Column("amount", Integer))
    currency: Column = no_init_field(Column("currency", Text))
    ledger_id: Column = no_init_field(Column("ledger_id", Text))
    idempotency_key: Column = no_init_field(Column("idempotency_key", Text))
    type: Column = no_init_field(Column("payer_type", Text))
    context: Column = no_init_field(Column("context", JSON))
    metadata: Column = no_init_field(Column("metadata", JSON))
    created_at: Column = no_init_field(Column("created_at", DateTime(False)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(False)))
