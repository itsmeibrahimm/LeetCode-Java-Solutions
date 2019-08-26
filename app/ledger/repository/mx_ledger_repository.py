from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Tuple
from abc import abstractmethod
from dataclasses import dataclass

from sqlalchemy import and_

from app.commons.database.client.aiopg import AioTransaction
from app.ledger.core.data_types import (
    InsertMxLedgerInput,
    InsertMxLedgerOutput,
    UpdateMxLedgerSetInput,
    UpdateMxLedgerWhereInput,
    UpdateMxLedgerOutput,
    GetMxLedgerByIdInput,
    GetMxLedgerByIdOutput,
    GetMxLedgerByAccountInput,
    GetMxLedgerByAccountOutput,
    InsertMxTransactionOutput,
    InsertMxTransactionInput,
    ProcessMxLedgerInput,
    ProcessMxLedgerOutput,
)
from app.ledger.core.types import MxTransactionType, MxLedgerStateType
from app.ledger.models.paymentdb import (
    mx_ledgers,
    mx_transactions,
    mx_scheduled_ledgers,
)

from app.ledger.repository.base import LedgerDBRepository


class MxLedgerRepositoryInterface:
    @abstractmethod
    async def insert_mx_ledger(
        self, request: InsertMxLedgerInput
    ) -> InsertMxLedgerOutput:
        ...

    @abstractmethod
    async def update_mx_ledger_balance(
        self,
        request_set: UpdateMxLedgerSetInput,
        request_where: UpdateMxLedgerWhereInput,
    ) -> UpdateMxLedgerOutput:
        ...

    @abstractmethod
    async def process_mx_ledger_state_and_close_schedule_ledger(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        ...

    @abstractmethod
    async def get_ledger_by_id(
        self, request: GetMxLedgerByIdInput
    ) -> Optional[GetMxLedgerByIdOutput]:
        ...

    @abstractmethod
    async def get_open_ledger_for_payment_account(
        self, request: GetMxLedgerByAccountInput
    ) -> Optional[GetMxLedgerByAccountOutput]:
        ...

    @abstractmethod
    async def create_one_off_mx_ledger(
        self, request_ledger: InsertMxLedgerInput
    ) -> Tuple[InsertMxLedgerOutput, InsertMxTransactionOutput]:
        ...


@dataclass
class MxLedgerRepository(MxLedgerRepositoryInterface, LedgerDBRepository):
    async def insert_mx_ledger(
        self, request: InsertMxLedgerInput
    ) -> InsertMxLedgerOutput:
        stmt = (
            mx_ledgers.table.insert()
            .values(request.dict(skip_defaults=True))
            .returning(*mx_ledgers.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        assert row
        return InsertMxLedgerOutput.from_row(row)

    async def update_mx_ledger_balance(
        self,
        request_set: UpdateMxLedgerSetInput,
        request_where: UpdateMxLedgerWhereInput,
    ) -> UpdateMxLedgerOutput:
        stmt = (
            mx_ledgers.table.update()
            .where(mx_ledgers.id == request_where.id)
            .values(request_set.dict(skip_defaults=True))
            .returning(*mx_ledgers.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        assert row
        return UpdateMxLedgerOutput.from_row(row)

    async def process_mx_ledger_state_and_close_schedule_ledger(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        async with self.payment_database.master().transaction() as tx:  # type: AioTransaction
            connection = tx.connection()
            try:
                # update ledger state to PROCESSING
                ledger_stmt = (
                    mx_ledgers.table.update()
                    .where(mx_ledgers.id == request.id)
                    .values(state=MxLedgerStateType.PROCESSING)
                    .returning(*mx_ledgers.table.columns.values())
                )
                ledger_row = await connection.fetch_one(ledger_stmt)
                assert ledger_row
            except Exception as e:
                raise e
            try:
                # update scheduled_ledger closed_at only when it is 0
                scheduled_ledger_stmt = (
                    mx_scheduled_ledgers.table.update()
                    .where(
                        and_(
                            mx_scheduled_ledgers.ledger_id == request.id,
                            mx_scheduled_ledgers.closed_at == 0,
                        )
                    )
                    .values(closed_at=datetime.utcnow().microsecond)
                    .returning(*mx_scheduled_ledgers.table.columns.values())
                )
                await connection.fetch_one(scheduled_ledger_stmt)
            except Exception as e:
                raise e
        return ProcessMxLedgerOutput.from_row(ledger_row)

    async def get_ledger_by_id(
        self, request: GetMxLedgerByIdInput
    ) -> Optional[GetMxLedgerByIdOutput]:
        stmt = mx_ledgers.table.select().where(mx_ledgers.id == request.id)
        row = await self.payment_database.master().fetch_one(stmt)
        return GetMxLedgerByIdOutput.from_row(row) if row else None

    async def get_open_ledger_for_payment_account(
        self, request: GetMxLedgerByAccountInput
    ) -> Optional[GetMxLedgerByAccountOutput]:
        stmt = mx_ledgers.table.select().where(
            and_(
                mx_ledgers.payment_account_id == request.payment_account_id,
                mx_ledgers.state == MxLedgerStateType.OPEN,
            )
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return GetMxLedgerByAccountOutput.from_row(row) if row else None

    # todo: lock db transaction here as well
    async def create_one_off_mx_ledger(
        self, request_ledger: InsertMxLedgerInput
    ) -> Tuple[InsertMxLedgerOutput, InsertMxTransactionOutput]:
        # create one off mx ledger
        one_off_mx_ledger = await self.insert_mx_ledger(request_ledger)
        # create mx transaction with given ledger id
        mx_transaction_id = uuid.uuid4()
        ide_key = str(uuid.uuid4())
        mx_transaction_to_insert = InsertMxTransactionInput(
            id=mx_transaction_id,
            payment_account_id=one_off_mx_ledger.payment_account_id,
            amount=one_off_mx_ledger.balance,
            currency=one_off_mx_ledger.currency,
            ledger_id=one_off_mx_ledger.id,
            idempotency_key=ide_key,
            target_type=MxTransactionType.MICRO_DEPOSIT,
            routing_key=datetime.utcnow(),
        )
        stmt = (
            mx_transactions.table.insert()
            .values(mx_transaction_to_insert.dict(skip_defaults=True))
            .returning(*mx_transactions.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        assert row
        mx_transaction = InsertMxTransactionOutput.from_row(row)

        # todo: call payout service to payout the ledger and update corresponding status

        return one_off_mx_ledger, mx_transaction
