from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Integer, Text, JSON
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MxTransactionTable(TableDefinition):
    name: str = no_init_field("mx_transactions")
    id: Column = no_init_field(Column("id", Text, primary_key=True))
    payment_account_id: Column = no_init_field(Column("payment_account_id", Text))
    amount: Column = no_init_field(Column("amount", Integer))
    currency: Column = no_init_field(Column("currency", Text))
    target_type: Column = no_init_field(Column("target_type", Text))
    ledger_id: Column = no_init_field(Column("ledger_id", Text))
    idempotency_key: Column = no_init_field(Column("idempotency_key", Text))

    # created_at for transaction from DSJ or POS confirmation time
    routing_key: Column = no_init_field(Column("routing_key", DateTime(False)))
    target_id: Column = no_init_field(Column("target_id", Text))
    legacy_transaction_id: Column = no_init_field(
        Column("legacy_transaction_id", Text)
    )  # only exists for mirgration purpose
    context: Column = no_init_field(Column("context", JSON))
    metadata: Column = no_init_field(Column("metadata", JSON))
    created_at: Column = no_init_field(
        Column("created_at", DateTime(False))
    )  # timestamp for db record insertion
    updated_at: Column = no_init_field(Column("updated_at", DateTime(False)))
