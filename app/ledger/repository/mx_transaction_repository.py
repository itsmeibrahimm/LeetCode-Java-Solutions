from __future__ import annotations

import uuid
from abc import abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.ledger.core.data_types import (
    InsertMxTransactionInput,
    InsertMxTransactionOutput,
    InsertMxTransactionWithLedgerInput,
    InsertMxLedgerInput,
    InsertMxLedgerOutput,
    InsertMxScheduledLedgerInput,
    GetMxLedgerByIdOutput,
    UpdateMxLedgerSetInput,
)
from app.ledger.core.types import MxLedgerStateType
from app.ledger.models.paymentdb import (
    mx_transactions,
    mx_ledgers,
    mx_scheduled_ledgers,
)
from app.ledger.repository.base import LedgerDBRepository
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)


class MxTransactionRepositoryInterface:
    @abstractmethod
    async def insert_mx_transaction(
        self, request: InsertMxTransactionInput
    ) -> InsertMxTransactionOutput:
        ...

    @abstractmethod
    async def create_ledger_and_insert_mx_transaction(
        self,
        request: InsertMxTransactionWithLedgerInput,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ) -> InsertMxTransactionOutput:
        ...

    @abstractmethod
    async def insert_mx_transaction_and_update_ledger(
        self,
        request: InsertMxTransactionWithLedgerInput,
        mx_ledger_repository: MxLedgerRepository,
        mx_ledger_id: UUID,
    ) -> InsertMxTransactionOutput:
        ...


@dataclass
class MxTransactionRepository(MxTransactionRepositoryInterface, LedgerDBRepository):
    async def insert_mx_transaction(
        self, request: InsertMxTransactionInput
    ) -> InsertMxTransactionOutput:
        stmt = (
            mx_transactions.table.insert()
            .values(request.dict(skip_defaults=True))
            .returning(*mx_transactions.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        assert row
        return InsertMxTransactionOutput.from_row(row)

    async def create_ledger_and_insert_mx_transaction(
        self,
        request: InsertMxTransactionWithLedgerInput,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ) -> InsertMxTransactionOutput:
        paymentdb_conn = self.payment_database.master()
        async with paymentdb_conn.transaction():
            try:
                # construct mx_ledger and insert
                mx_ledger_id = uuid.uuid4()
                mx_ledger_to_insert = InsertMxLedgerInput(
                    id=mx_ledger_id,
                    type=request.type,
                    currency=request.currency,
                    state=MxLedgerStateType.OPEN.value,
                    balance=request.amount,
                    payment_account_id=request.payment_account_id,
                    amount_paid=0,
                )
                ledger_stmt = (
                    mx_ledgers.table.insert()
                    .values(mx_ledger_to_insert.dict(skip_defaults=True))
                    .returning(*mx_ledgers.table.columns.values())
                )
                ledger_row = await paymentdb_conn.fetch_one(ledger_stmt)
                assert ledger_row
                created_mx_ledger = InsertMxLedgerOutput.from_row(ledger_row)
            except Exception as e:
                raise e
            try:
                # construct mx_scheduled_ledger and insert
                mx_scheduled_ledger_id = uuid.uuid4()
                mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
                    id=mx_scheduled_ledger_id,
                    payment_account_id=request.payment_account_id,
                    ledger_id=created_mx_ledger.id,
                    interval_type=request.interval_type,
                    closed_at=0,
                    start_time=mx_scheduled_ledger_repository.pacific_start_time_for_current_interval(
                        request.routing_key, request.interval_type
                    ),
                    end_time=mx_scheduled_ledger_repository.pacific_end_time_for_current_interval(
                        request.routing_key, request.interval_type
                    ),
                )
                scheduled_ledger_stmt = (
                    mx_scheduled_ledgers.table.insert()
                    .values(mx_scheduled_ledger_to_insert.dict(skip_defaults=True))
                    .returning(*mx_scheduled_ledgers.table.columns.values())
                )
                await paymentdb_conn.fetch_one(scheduled_ledger_stmt)
            except Exception as e:
                raise e
            try:
                # construct mx_transaction and insert
                mx_transaction_to_insert = InsertMxTransactionInput(
                    id=uuid.uuid4(),
                    payment_account_id=request.payment_account_id,
                    amount=request.amount,
                    currency=request.currency,
                    ledger_id=created_mx_ledger.id,
                    idempotency_key=request.idempotency_key,
                    routing_key=request.routing_key,
                    target_type=request.target_type,
                    target_id=request.target_id,
                    legacy_transaction_id=request.legacy_transaction_id,
                    context=request.context,
                    metadata=request.metadata,
                )
                txn_stmt = (
                    mx_transactions.table.insert()
                    .values(mx_transaction_to_insert.dict(skip_defaults=True))
                    .returning(*mx_transactions.table.columns.values())
                )
                txn_row = await paymentdb_conn.fetch_one(txn_stmt)
                assert txn_row
                mx_transaction = InsertMxTransactionOutput.from_row(txn_row)
            except Exception as e:
                raise e
        return mx_transaction

    # todo: add error handling for ledger lock
    async def insert_mx_transaction_and_update_ledger(
        self,
        request: InsertMxTransactionWithLedgerInput,
        mx_ledger_repository: MxLedgerRepository,
        mx_ledger_id: UUID,
    ) -> InsertMxTransactionOutput:
        paymentdb_conn = self.payment_database.master()
        async with paymentdb_conn.transaction():
            try:
                # Lock the row for updating the balance
                stmt = (
                    mx_ledgers.table.select()
                    .where(mx_ledgers.id == mx_ledger_id)
                    .with_for_update(nowait=True)
                )
                row = await paymentdb_conn.fetch_one(stmt)
                assert row
                mx_ledger = GetMxLedgerByIdOutput.from_row(row)
            except Exception as e:
                raise e
            try:
                # construct update request and update mx_ledger balance
                updated_amount = mx_ledger.balance + request.amount
                request_balance = UpdateMxLedgerSetInput(balance=updated_amount)
                stmt = (
                    mx_ledgers.table.update()
                    .where(mx_ledgers.id == mx_ledger.id)
                    .values(request_balance.dict(skip_defaults=True))
                    .returning(*mx_ledgers.table.columns.values())
                )
                await paymentdb_conn.fetch_one(stmt)
            except Exception as e:
                raise e
            try:
                # construct mx_transaction and insert
                mx_transaction_to_insert = InsertMxTransactionInput(
                    id=uuid.uuid4(),
                    payment_account_id=request.payment_account_id,
                    amount=request.amount,
                    currency=request.currency,
                    ledger_id=mx_ledger.id,
                    idempotency_key=request.idempotency_key,
                    routing_key=request.routing_key,
                    target_type=request.target_type,
                    target_id=request.target_id,
                    legacy_transaction_id=request.legacy_transaction_id,
                    context=request.context,
                    metadata=request.metadata,
                )
                txn_stmt = (
                    mx_transactions.table.insert()
                    .values(mx_transaction_to_insert.dict(skip_defaults=True))
                    .returning(*mx_transactions.table.columns.values())
                )
                txn_row = await paymentdb_conn.fetch_one(txn_stmt)
                assert txn_row
                mx_transaction = InsertMxTransactionOutput.from_row(txn_row)
            except Exception as e:
                raise e
        return mx_transaction
