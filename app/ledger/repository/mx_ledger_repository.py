from __future__ import annotations

import uuid
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import and_

from app.commons import tracing
from app.commons.database.client.interface import DBConnection
from app.ledger.core.data_types import (
    InsertMxLedgerInput,
    InsertMxLedgerOutput,
    UpdateMxLedgerSetInput,
    UpdateMxLedgerWhereInput,
    UpdateMxLedgerOutput,
    GetMxLedgerByIdInput,
    GetMxLedgerByIdOutput,
    ProcessMxLedgerInput,
    ProcessMxLedgerOutput,
    UpdatePaidMxLedgerInput,
    UpdatedRolledMxLedgerInput,
    RolloverNegativeLedgerInput,
    InsertMxTransactionWithLedgerInput,
)
from app.ledger.core.types import (
    MxTransactionType,
    MxLedgerStateType,
    MxScheduledLedgerIntervalType,
)

from app.ledger.models.paymentdb import mx_ledgers, mx_scheduled_ledgers
from app.ledger.repository.base import LedgerDBRepository
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository


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
    async def move_ledger_state_to_processing_and_close_schedule_ledger(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        ...

    @abstractmethod
    async def get_ledger_by_id(
        self, request: GetMxLedgerByIdInput
    ) -> Optional[GetMxLedgerByIdOutput]:
        ...

    @abstractmethod
    async def move_ledger_state_to_failed(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        ...

    @abstractmethod
    async def move_ledger_state_to_paid(
        self, request: UpdatePaidMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        ...

    @abstractmethod
    async def move_ledger_state_to_rolled(
        self, request: UpdatedRolledMxLedgerInput, db_connection: DBConnection
    ) -> ProcessMxLedgerOutput:
        ...

    @abstractmethod
    async def move_ledger_state_to_submitted(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        ...

    @abstractmethod
    async def rollover_negative_balanced_ledger(
        self,
        request: RolloverNegativeLedgerInput,
        mx_transaction_repo: MxTransactionRepository,
    ) -> ProcessMxLedgerOutput:
        ...


@dataclass
@tracing.track_breadcrumb(repository_name="mx_ledger")
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

    async def move_ledger_state_to_processing_and_close_schedule_ledger(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        async with self.payment_database.master().transaction() as tx:
            connection = tx.connection()
            try:
                # Lock mx_ledger row for updating state
                stmt = (
                    mx_ledgers.table.select()
                    .where(mx_ledgers.id == request.id)
                    .with_for_update(nowait=True)
                )
                await connection.fetch_one(stmt)
            except Exception as e:
                raise e
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
                    .values(closed_at=int(datetime.utcnow().timestamp() * 1000000))
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

    async def move_ledger_state_to_failed(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        now = datetime.utcnow()
        try:
            # update ledger state to FAILED and finalized_at, updated_at
            ledger_stmt = (
                mx_ledgers.table.update()
                .where(mx_ledgers.id == request.id)
                .values(
                    state=MxLedgerStateType.FAILED, finalized_at=now, updated_at=now
                )
                .returning(*mx_ledgers.table.columns.values())
            )
            ledger_row = await self.payment_database.master().fetch_one(ledger_stmt)
            assert ledger_row
        except Exception as e:
            raise e
        return ProcessMxLedgerOutput.from_row(ledger_row)

    async def move_ledger_state_to_paid(
        self, request: UpdatePaidMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        now = datetime.utcnow()
        try:
            # update ledger state to PAID and update amount_paid and finalized_at, updated_at
            ledger_stmt = (
                mx_ledgers.table.update()
                .where(mx_ledgers.id == request.id)
                .values(
                    state=MxLedgerStateType.PAID,
                    amount_paid=request.amount_paid,
                    finalized_at=now,
                    updated_at=now,
                )
                .returning(*mx_ledgers.table.columns.values())
            )
            ledger_row = await self.payment_database.master().fetch_one(ledger_stmt)
            assert ledger_row
        except Exception as e:
            raise e
        return ProcessMxLedgerOutput.from_row(ledger_row)

    async def move_ledger_state_to_rolled(
        self, request: UpdatedRolledMxLedgerInput, db_connection: DBConnection
    ) -> ProcessMxLedgerOutput:
        now = datetime.utcnow()
        try:
            # update ledger state to ROLLED, amount_paid, finalized_at, rolled_to_ledger_id, updated_at
            ledger_stmt = (
                mx_ledgers.table.update()
                .where(mx_ledgers.id == request.id)
                .values(
                    state=MxLedgerStateType.ROLLED,
                    amount_paid=0,
                    finalized_at=now,
                    rolled_to_ledger_id=request.rolled_to_ledger_id,
                    updated_at=now,
                )
                .returning(*mx_ledgers.table.columns.values())
            )
            ledger_row = await self.payment_database.master().fetch_one(ledger_stmt)
            assert ledger_row
        except Exception as e:
            raise e
        return ProcessMxLedgerOutput.from_row(ledger_row)

    async def move_ledger_state_to_submitted(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        now = datetime.utcnow()
        try:
            # update ledger state to SUBMITTED, submitted_at, updated_at
            ledger_stmt = (
                mx_ledgers.table.update()
                .where(mx_ledgers.id == request.id)
                .values(
                    state=MxLedgerStateType.SUBMITTED, submitted_at=now, updated_at=now
                )
                .returning(*mx_ledgers.table.columns.values())
            )
            ledger_row = await self.payment_database.master().fetch_one(ledger_stmt)
            assert ledger_row
        except Exception as e:
            raise e
        return ProcessMxLedgerOutput.from_row(ledger_row)

    # todo: PAY-3482: refactor type of the output

    async def rollover_negative_balanced_ledger(
        self,
        request: RolloverNegativeLedgerInput,
        mx_transaction_repo: MxTransactionRepository,
    ) -> ProcessMxLedgerOutput:
        # given ledger_id can always find a ledger, it is checked in ledger processor.py
        mx_ledger = await self.get_ledger_by_id(GetMxLedgerByIdInput(id=request.id))
        assert mx_ledger
        request_input = InsertMxTransactionWithLedgerInput(
            currency=mx_ledger.currency,
            amount=mx_ledger.balance,
            type=mx_ledger.type,
            payment_account_id=mx_ledger.payment_account_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=datetime.utcnow(),
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.NEGATIVE_BALANCE_ROLLOVER,
        )

        async with self.payment_database.master().transaction() as tx:
            connection = tx.connection()
            try:
                mx_transaction = await mx_transaction_repo.create_mx_transaction_and_upsert_mx_ledgers(
                    request_input, connection
                )
                # move the ledger state to rolled
                closed_mx_ledger = await self.move_ledger_state_to_rolled(
                    UpdatedRolledMxLedgerInput(
                        id=request.id, rolled_to_ledger_id=mx_transaction.ledger_id
                    ),
                    connection,
                )
                return closed_mx_ledger
            except Exception as e:
                raise e
