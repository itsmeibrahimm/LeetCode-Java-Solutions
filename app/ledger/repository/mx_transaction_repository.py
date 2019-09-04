from __future__ import annotations

import logging
import uuid
from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional
from typing import Tuple
from uuid import UUID

from sqlalchemy import and_

from app.commons import tracing
from app.commons.database.client.interface import DBConnection
from app.ledger.core.data_types import (
    InsertMxTransactionInput,
    InsertMxTransactionOutput,
    InsertMxTransactionWithLedgerInput,
    InsertMxLedgerInput,
    InsertMxLedgerOutput,
    InsertMxScheduledLedgerInput,
    GetMxLedgerByIdOutput,
    UpdateMxLedgerSetInput,
    GetMxScheduledLedgerInput,
    GetMxScheduledLedgerOutput,
    GetMxScheduledLedgerByAccountInput,
)
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.types import MxLedgerStateType
from app.ledger.core.utils import (
    to_mx_transaction,
    pacific_start_time_for_current_interval,
    pacific_end_time_for_current_interval,
)
from app.ledger.core.types import MxLedgerStateType, MxLedgerType
from app.ledger.core.utils import MX_LEDGER_TYPE_MUST_HAVE_MX_SCHEDULED_LEDGER
from app.ledger.models.paymentdb import (
    mx_transactions,
    mx_ledgers,
    mx_scheduled_ledgers,
)
from app.ledger.repository.base import LedgerDBRepository

logger = logging.getLogger(__name__)


class MxTransactionRepositoryInterface:
    @abstractmethod
    async def insert_mx_transaction(
        self, request: InsertMxTransactionInput
    ) -> InsertMxTransactionOutput:
        ...

    @abstractmethod
    async def create_ledger_and_insert_mx_transaction(
        self, request: InsertMxTransactionWithLedgerInput, db_connection: DBConnection
    ) -> Tuple[InsertMxLedgerOutput, InsertMxTransactionOutput]:
        ...

    @abstractmethod
    async def insert_mx_transaction_and_update_ledger(
        self,
        request: InsertMxTransactionWithLedgerInput,
        mx_ledger_id: UUID,
        db_connection: DBConnection,
    ) -> InsertMxTransactionOutput:
        ...

    @abstractmethod
    async def get_open_mx_scheduled_ledger_with_period(
        self, request: GetMxScheduledLedgerInput, db_connection: DBConnection
    ) -> Optional[GetMxScheduledLedgerOutput]:
        ...

    @abstractmethod
    async def get_open_mx_scheduled_ledger_for_payment_account_id(
        self, request: GetMxScheduledLedgerByAccountInput, db_connection: DBConnection
    ) -> Optional[GetMxScheduledLedgerOutput]:
        ...

    @abstractmethod
    async def create_mx_transaction_and_upsert_mx_ledgers(
        self,
        input_request: InsertMxTransactionWithLedgerInput,
        db_connection: DBConnection,
    ) -> MxTransaction:
        ...


@dataclass
@tracing.set_repository_name("mx_transaction", only_trackable=False)
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

    async def create_ledger_and_insert_mx_transaction_caller(
        self, request: InsertMxTransactionWithLedgerInput
    ):
        async with self.payment_database.master().acquire() as connection:  # type: DBConnection
            try:
                mx_ledger, mx_transaction = await self.create_ledger_and_insert_mx_transaction(
                    request, connection
                )
                return mx_ledger, mx_transaction
            except Exception as e:
                raise e

    async def create_ledger_and_insert_mx_transaction(
        self, request: InsertMxTransactionWithLedgerInput, db_connection: DBConnection
    ) -> Tuple[InsertMxLedgerOutput, InsertMxTransactionOutput]:
        async with db_connection.transaction():
            try:
                # construct mx_ledger and insert
                mx_ledger_id = uuid.uuid4()
                mx_ledger_to_insert = InsertMxLedgerInput(
                    id=mx_ledger_id,
                    type=request.type,
                    currency=request.currency,
                    state=MxLedgerStateType.PROCESSING.value
                    if request.type == MxLedgerType.MICRO_DEPOSIT
                    else MxLedgerStateType.OPEN.value,
                    balance=request.amount,
                    payment_account_id=request.payment_account_id,
                )
                ledger_stmt = (
                    mx_ledgers.table.insert()
                    .values(mx_ledger_to_insert.dict(skip_defaults=True))
                    .returning(*mx_ledgers.table.columns.values())
                )
                ledger_row = await db_connection.fetch_one(ledger_stmt)
                assert ledger_row
                created_mx_ledger = InsertMxLedgerOutput.from_row(ledger_row)
            except Exception as e:
                raise e
            # skip when created ledger type is micro-deposit
            if request.type in MX_LEDGER_TYPE_MUST_HAVE_MX_SCHEDULED_LEDGER:
                if request.interval_type is None:
                    raise Exception(
                        "interval_type is required when leger type is in MX_LEDGER_TYPE_MUST_HAVE_MX_SCHEDULED_LEDGER"
                    )
                try:
                    # construct mx_scheduled_ledger and insert
                    mx_scheduled_ledger_id = uuid.uuid4()
                    mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
                        id=mx_scheduled_ledger_id,
                        payment_account_id=request.payment_account_id,
                        ledger_id=created_mx_ledger.id,
                        interval_type=request.interval_type,
                        closed_at=0,
                        start_time=pacific_start_time_for_current_interval(
                            request.routing_key, request.interval_type
                        ),
                        end_time=pacific_end_time_for_current_interval(
                            request.routing_key, request.interval_type
                        ),
                    )
                    scheduled_ledger_stmt = (
                        mx_scheduled_ledgers.table.insert()
                        .values(mx_scheduled_ledger_to_insert.dict(skip_defaults=True))
                        .returning(*mx_scheduled_ledgers.table.columns.values())
                    )
                    await db_connection.fetch_one(scheduled_ledger_stmt)
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
                txn_row = await db_connection.fetch_one(txn_stmt)
                assert txn_row
                mx_transaction = InsertMxTransactionOutput.from_row(txn_row)
            except Exception as e:
                raise e
        return created_mx_ledger, mx_transaction

    async def insert_mx_transaction_and_update_ledger(
        self,
        request: InsertMxTransactionWithLedgerInput,
        mx_ledger_id: UUID,
        db_connection: DBConnection,
    ) -> InsertMxTransactionOutput:
        try:
            async with db_connection.transaction():
                try:
                    # Lock the row for updating the balance
                    stmt = (
                        mx_ledgers.table.select()
                        .where(mx_ledgers.id == mx_ledger_id)
                        .with_for_update(nowait=True)
                    )
                    row = await db_connection.fetch_one(stmt)
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
                    await db_connection.fetch_one(stmt)
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
                    txn_row = await db_connection.fetch_one(txn_stmt)
                    assert txn_row
                    mx_transaction = InsertMxTransactionOutput.from_row(txn_row)
                except Exception as e:
                    raise e
                return mx_transaction
        except Exception as e:
            raise e

    async def get_open_mx_scheduled_ledger_with_period(
        self, request: GetMxScheduledLedgerInput, db_connection: DBConnection
    ) -> Optional[GetMxScheduledLedgerOutput]:
        """
        Get mx_scheduled_ledger with given payment_account_id, routing_key, interval_type and corresponding open mx ledger
        Filter specific start_time and end_time to avoid multiple existing scheduled ledger with same start_time
        :param db_connection: DBConnection
        :param request: GetMxScheduledLedgerInput
        :return: GetMxScheduledLedgerOutput
        """
        stmt = mx_scheduled_ledgers.table.select().where(
            and_(
                mx_scheduled_ledgers.payment_account_id
                == request.payment_account_id,  # noqa: W503
                mx_scheduled_ledgers.start_time
                == pacific_start_time_for_current_interval(  # noqa: W503
                    request.routing_key, request.interval_type
                ),
                mx_scheduled_ledgers.end_time
                == pacific_end_time_for_current_interval(  # noqa: W503
                    request.routing_key, request.interval_type
                ),
                mx_ledgers.state == MxLedgerStateType.OPEN,
                mx_ledgers.table.c.id == mx_scheduled_ledgers.ledger_id,
            )
        )
        row = await db_connection.fetch_one(stmt)
        return GetMxScheduledLedgerOutput.from_row(row) if row else None

    async def get_open_mx_scheduled_ledger_for_payment_account_id(
        self, request: GetMxScheduledLedgerByAccountInput, db_connection: DBConnection
    ) -> Optional[GetMxScheduledLedgerOutput]:
        """
        Get the first mx_scheduled_ledger with given payment_account_id and also 0 for closed_at value, and order by
        (end_time, start_time)
        :param db_connection: DBConnection
        :param request: GetMxLedgerByAccountInput
        :return: GetMxScheduledLedgerOutput
        """
        stmt = (
            mx_scheduled_ledgers.table.select()
            .where(
                and_(
                    mx_scheduled_ledgers.payment_account_id
                    == request.payment_account_id,
                    mx_scheduled_ledgers.closed_at == 0,
                )
            )
            .order_by(
                mx_scheduled_ledgers.end_time.asc(),
                mx_scheduled_ledgers.start_time.asc(),
            )
        )
        row = await db_connection.fetch_one(stmt)
        return GetMxScheduledLedgerOutput.from_row(row) if row else None

    async def create_mx_transaction_and_upsert_mx_ledgers_caller(
        self, request_input: InsertMxTransactionWithLedgerInput
    ):
        async with self.payment_database.master().acquire() as connection:  # type: DBConnection
            try:
                mx_transaction = await self.create_mx_transaction_and_upsert_mx_ledgers(
                    request_input, connection
                )
                return mx_transaction
            except Exception as e:
                raise e

    async def create_mx_transaction_and_upsert_mx_ledgers(
        self,
        request_input: InsertMxTransactionWithLedgerInput,
        db_connection: DBConnection,
    ) -> MxTransaction:
        """
        Create mx_transaction and insert/update mx_ledgers
        :param db_connection: DBConnection
        :param request_input: InsertMxTransactionWithLedgerInput
        :return: MxTransaction
        """
        get_scheduled_ledger_request = GetMxScheduledLedgerInput(
            payment_account_id=request_input.payment_account_id,
            routing_key=request_input.routing_key,
            interval_type=request_input.interval_type,
        )
        mx_scheduled_ledger = await self.get_open_mx_scheduled_ledger_with_period(
            get_scheduled_ledger_request, db_connection
        )
        mx_ledger_id = mx_scheduled_ledger.ledger_id if mx_scheduled_ledger else None

        try:
            # if not found, retrieve open ledger for current payment_account
            if not mx_scheduled_ledger:
                get_mx_scheduled_ledger_request = GetMxScheduledLedgerByAccountInput(
                    payment_account_id=request_input.payment_account_id
                )
                mx_scheduled_ledger = await self.get_open_mx_scheduled_ledger_for_payment_account_id(
                    get_mx_scheduled_ledger_request, db_connection
                )
                # if not found, create new mx_scheduled_ledger and mx_ledger
                # if open ledger found, but the mx_txn routing_key is late than the end_time of found ledger
                # we will need to create new ledger for the mx_txn
                if (
                    not mx_scheduled_ledger
                    or mx_scheduled_ledger.end_time < request_input.routing_key
                ):
                    try:
                        created_ledger, created_txn = await self.create_ledger_and_insert_mx_transaction(
                            request_input, db_connection
                        )
                        return to_mx_transaction(created_txn)
                    except Exception as e:
                        raise e
                else:
                    mx_ledger_id = mx_scheduled_ledger.ledger_id

            # create transaction attached and update balance with given mx_ledger_id
            assert mx_ledger_id  # no exceptions should be raised from the assertion
            try:
                created_mx_txn = await self.insert_mx_transaction_and_update_ledger(
                    request_input, mx_ledger_id, db_connection
                )
            except Exception as e:
                raise e
        except Exception as e:
            raise e
        return to_mx_transaction(created_mx_txn)
