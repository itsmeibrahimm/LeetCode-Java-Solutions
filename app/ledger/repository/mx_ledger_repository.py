from __future__ import annotations

import uuid
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

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
    UpdatePaidMxLedgerInput,
    UpdatedRolledMxLedgerInput,
    RolloverNegativeLedgerInput,
    RolloverNegativeLedgerOutput,
    InsertMxScheduledLedgerInput,
)
from app.ledger.core.types import (
    MxTransactionType,
    MxLedgerStateType,
    MxLedgerType,
    MxScheduledLedgerIntervalType,
)
from app.ledger.core.utils import (
    pacific_start_time_for_current_interval,
    pacific_end_time_for_current_interval,
)
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
    async def get_open_ledger_for_payment_account(
        self, request: GetMxLedgerByAccountInput
    ) -> Optional[GetMxLedgerByAccountOutput]:
        ...

    @abstractmethod
    async def rollover_negative_ledger_to_open_ledger(
        self, request: RolloverNegativeLedgerInput, open_ledger_id: UUID
    ) -> RolloverNegativeLedgerOutput:
        ...

    @abstractmethod
    async def rollover_negative_ledger_to_new_ledger(
        self, request: RolloverNegativeLedgerInput
    ) -> RolloverNegativeLedgerOutput:
        ...

    @abstractmethod
    async def create_one_off_mx_ledger(
        self, request_ledger: InsertMxLedgerInput
    ) -> Tuple[InsertMxLedgerOutput, InsertMxTransactionOutput]:
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
        self, request: UpdatedRolledMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        ...

    @abstractmethod
    async def move_ledger_state_to_submitted(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
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

    async def move_ledger_state_to_processing_and_close_schedule_ledger(
        self, request: ProcessMxLedgerInput
    ) -> ProcessMxLedgerOutput:
        async with self.payment_database.master().transaction() as tx:  # type: AioTransaction
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
        self, request: UpdatedRolledMxLedgerInput
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

    async def rollover_negative_ledger_to_open_ledger(
        self, request: RolloverNegativeLedgerInput, open_ledger_id: UUID
    ) -> RolloverNegativeLedgerOutput:
        async with self.payment_database.master().transaction() as tx:  # type: AioTransaction
            connection = tx.connection()
            try:
                # try to obtain the negative ledger
                negative_mx_ledger_row_stmt = (
                    mx_ledgers.table.select()
                    .where(mx_ledgers.id == request.id)
                    .with_for_update(nowait=True)
                )
                negative_mx_ledger_row = await connection.fetch_one(
                    negative_mx_ledger_row_stmt
                )
                assert negative_mx_ledger_row
                negative_mx_ledger = GetMxLedgerByIdOutput.from_row(
                    negative_mx_ledger_row
                )
                assert negative_mx_ledger
            except Exception as e:
                raise e
            try:
                # Lock the row of open ledger for updating balance
                open_mx_ledger_row_stmt = (
                    mx_ledgers.table.select()
                    .where(mx_ledgers.id == open_ledger_id)
                    .with_for_update(nowait=True)
                )
                open_mx_ledger_row = await connection.fetch_one(open_mx_ledger_row_stmt)
                assert open_mx_ledger_row
                open_mx_ledger = GetMxLedgerByIdOutput.from_row(open_mx_ledger_row)
                assert open_mx_ledger
            except Exception as e:
                raise e
            try:
                # construct request and update balance of the open mx_ledger
                updated_amount = open_mx_ledger.balance + negative_mx_ledger.balance
                request_balance = UpdateMxLedgerSetInput(balance=updated_amount)
                stmt = (
                    mx_ledgers.table.update()
                    .where(mx_ledgers.id == open_ledger_id)
                    .values(request_balance.dict(skip_defaults=True))
                    .returning(*mx_ledgers.table.columns.values())
                )
                updated_open_ledger_row = await connection.fetch_one(stmt)
                assert updated_open_ledger_row
                updated_open_ledger = UpdateMxLedgerOutput.from_row(open_mx_ledger_row)
            except Exception as e:
                raise e
            try:
                # construct mx_transaction and attach to open mx_ledger
                mx_transaction_to_insert = InsertMxTransactionInput(
                    id=uuid.uuid4(),
                    payment_account_id=open_mx_ledger.payment_account_id,
                    amount=negative_mx_ledger.balance,
                    currency=updated_open_ledger.currency,
                    ledger_id=updated_open_ledger.id,
                    idempotency_key=str(uuid.uuid4()),
                    routing_key=datetime.utcnow(),
                    target_type=MxTransactionType.NEGATIVE_BALANCE_ROLLOVER.value,
                )
                txn_stmt = (
                    mx_transactions.table.insert()
                    .values(mx_transaction_to_insert.dict(skip_defaults=True))
                    .returning(*mx_transactions.table.columns.values())
                )
                await connection.fetch_one(txn_stmt)
            except Exception as e:
                raise e
        return updated_open_ledger

    async def rollover_negative_ledger_to_new_ledger(
        self, request: RolloverNegativeLedgerInput
    ) -> RolloverNegativeLedgerOutput:
        async with self.payment_database.master().transaction() as tx:  # type: AioTransaction
            connection = tx.connection()
            try:
                # try to obtain negative balance ledger
                negative_mx_ledger_row_stmt = (
                    mx_ledgers.table.select()
                    .where(mx_ledgers.id == request.id)
                    .with_for_update(nowait=True)
                )
                negative_mx_ledger_row = await connection.fetch_one(
                    negative_mx_ledger_row_stmt
                )
                assert negative_mx_ledger_row
                negative_mx_ledger = GetMxLedgerByIdOutput.from_row(
                    negative_mx_ledger_row
                )
                assert negative_mx_ledger
            except Exception as e:
                raise e
            try:
                mx_ledger_id = uuid.uuid4()
                # construct request and create new ledger with rollover balance
                mx_ledger_to_insert = InsertMxLedgerInput(
                    id=mx_ledger_id,
                    type=MxLedgerType.SCHEDULED.value,
                    currency=negative_mx_ledger.currency,
                    state=MxLedgerStateType.OPEN.value,
                    balance=negative_mx_ledger.balance,
                    payment_account_id=negative_mx_ledger.payment_account_id,
                )
                ledger_stmt = (
                    mx_ledgers.table.insert()
                    .values(mx_ledger_to_insert.dict(skip_defaults=True))
                    .returning(*mx_ledgers.table.columns.values())
                )
                ledger_row = await connection.fetch_one(ledger_stmt)
                assert ledger_row
                created_mx_ledger = InsertMxLedgerOutput.from_row(ledger_row)
                assert created_mx_ledger
            except Exception as e:
                raise e
            try:
                # construct mx_scheduled_ledger and insert
                routing_key = datetime.utcnow()
                mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
                    id=uuid.uuid4(),
                    payment_account_id=created_mx_ledger.payment_account_id,
                    ledger_id=created_mx_ledger.id,
                    interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
                    closed_at=0,
                    start_time=pacific_start_time_for_current_interval(
                        routing_key, MxScheduledLedgerIntervalType.WEEKLY
                    ),
                    end_time=pacific_end_time_for_current_interval(
                        routing_key, MxScheduledLedgerIntervalType.WEEKLY
                    ),
                )
                scheduled_ledger_stmt = (
                    mx_scheduled_ledgers.table.insert()
                    .values(mx_scheduled_ledger_to_insert.dict(skip_defaults=True))
                    .returning(*mx_scheduled_ledgers.table.columns.values())
                )
                await connection.fetch_one(scheduled_ledger_stmt)
            except Exception as e:
                raise e
            try:
                # construct mx_transaction and insert
                mx_transaction_to_insert = InsertMxTransactionInput(
                    id=uuid.uuid4(),
                    payment_account_id=created_mx_ledger.payment_account_id,
                    amount=created_mx_ledger.balance,
                    currency=created_mx_ledger.currency,
                    ledger_id=created_mx_ledger.id,
                    idempotency_key=str(uuid.uuid4()),
                    routing_key=routing_key,
                    target_type=MxTransactionType.NEGATIVE_BALANCE_ROLLOVER.value,
                )
                txn_stmt = (
                    mx_transactions.table.insert()
                    .values(mx_transaction_to_insert.dict(skip_defaults=True))
                    .returning(*mx_transactions.table.columns.values())
                )
                await connection.fetch_one(txn_stmt)
            except Exception as e:
                raise e
            return created_mx_ledger

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
