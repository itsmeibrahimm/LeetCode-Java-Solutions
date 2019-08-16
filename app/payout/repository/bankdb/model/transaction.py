from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, Text, text
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class TransactionTable(TableDefinition):
    name: str = no_init_field("transactions")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text("nextval('transactions_id_seq'::regclass)"),
        )
    )
    amount: Column = no_init_field(Column("amount", Integer, nullable=False))
    payment_account_id: Column = no_init_field(
        Column("payment_account_id", Integer, nullable=False)
    )
    transfer_id: Column = no_init_field(Column("amount", Integer))
    amount_paid: Column = no_init_field(Column("amount_paid", Integer, nullable=False))
    created_at: Column = no_init_field(
        Column("created_at", DateTime(True), nullable=False)
    )
    created_by_id: Column = no_init_field(Column("created_by_id", Integer))
    notes: Column = no_init_field(Column("notes", Text))
    metadata: Column = no_init_field(Column("metadata", Text))
    idempotency_key: Column = no_init_field(Column("idempotency_key", Text))
    currency: Column = no_init_field(Column("currency", Text))
    target_id: Column = no_init_field(Column("target_id", Integer))
    target_type: Column = no_init_field(Column("target_type", Text))
    state: Column = no_init_field(Column("state", Text))
    updated_at: Column = no_init_field(
        Column("updated_at", DateTime(True), nullable=False)
    )
    dsj_id: Column = no_init_field(Column("dsj_id", Integer))
    payout_id: Column = no_init_field(Column("payout_id", Integer))
    inserted_at: Column = no_init_field(Column("inserted_at", DateTime(True)))


class _TransactionPartial(DBEntity):
    amount: Optional[int]
    payment_account_id: Optional[int]
    transfer_id: Optional[int]
    amount_paid: Optional[int]
    created_at: Optional[datetime]
    created_by_id: Optional[int]
    notes: Optional[str]
    metadata: Optional[str]
    idempotency_key: Optional[str]
    currency: Optional[str]
    target_id: Optional[int]
    target_type: Optional[str]
    state: Optional[str]
    updated_at: Optional[datetime]
    dsj_id: Optional[int]
    payout_id: Optional[int]
    inserted_at: Optional[datetime]


class Transaction(_TransactionPartial):
    id: int
    amount: int
    payment_account_id: int
    amount_paid: int
    created_at: datetime
    updated_at: datetime


class TransactionCreate(_TransactionPartial):
    pass


class TransactionUpdate(_TransactionPartial):
    pass
