from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Tuple
from abc import abstractmethod
from dataclasses import dataclass
from uuid import UUID

from gino import GinoConnection

from app.commons.database.model import DBRequestModel, DBEntity
from app.ledger.core.mx_transaction.types import MxTransactionType
from app.ledger.models.paymentdb import mx_ledgers, mx_transactions


from app.ledger.repository.base import LedgerDBRepository


###########################################################
#       MxLedger DBEntity and CRUD operations             #
###########################################################
from app.ledger.repository.mx_transaction_repository import (
    InsertMxTransactionInput,
    InsertMxTransactionOutput,
)


class MxLedgerDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID
    type: str
    currency: str
    state: str
    balance: int
    payment_account_id: str
    legacy_transfer_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    submitted_at: Optional[datetime]
    amount_paid: Optional[int]
    finalized_at: Optional[datetime] = None
    created_by_employee_id: Optional[str] = None
    submitted_by_employee_id: Optional[str] = None
    rolled_to_ledger_id: Optional[str] = None


class InsertMxLedgerInput(MxLedgerDbEntity):
    pass


class InsertMxLedgerOutput(MxLedgerDbEntity):
    pass


class UpdateMxLedgerSetInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    balance: int


class UpdateMxLedgerWhereInput(DBRequestModel):
    id: UUID


class UpdateMxLedgerOutput(MxLedgerDbEntity):
    pass


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
    async def create_one_off_mx_ledger(
        self, request_ledger: InsertMxLedgerInput
    ) -> Tuple[InsertMxLedgerOutput, InsertMxTransactionOutput]:
        ...


@dataclass
class MxLedgerRepository(MxLedgerRepositoryInterface, LedgerDBRepository):
    async def insert_mx_ledger(
        self, request: InsertMxLedgerInput
    ) -> InsertMxLedgerOutput:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection

            stmt = (
                mx_ledgers.table.insert()
                .values(request.dict(skip_defaults=True))
                .returning(*mx_ledgers.table.columns.values())
            )
            row = await conn.first(stmt)
            return InsertMxLedgerOutput.from_orm(row)

    async def update_mx_ledger_balance(
        self,
        request_set: UpdateMxLedgerSetInput,
        request_where: UpdateMxLedgerWhereInput,
    ) -> UpdateMxLedgerOutput:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            stmt = (
                mx_ledgers.table.update()
                .where(mx_ledgers.id == request_where.id)
                .values(request_set.dict(skip_defaults=True))
                .returning(*mx_ledgers.table.columns.values())
            )
            row = await conn.execution_options(
                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return UpdateMxLedgerOutput.from_orm(row)

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
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            stmt = (
                mx_transactions.table.insert()
                .values(mx_transaction_to_insert.dict(skip_defaults=True))
                .returning(*mx_transactions.table.columns.values())
            )
            row = await conn.first(stmt)
            mx_transaction = InsertMxTransactionOutput.from_orm(row)

        # todo: call payout service to payout the ledger

        return one_off_mx_ledger, mx_transaction
