from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from gino import GinoConnection

from app.commons.database.model import DBEntity
from app.ledger.models.paymentdb import mx_transactions


###########################################################
#     MxTransaction DBEntity and CRUD operations          #
###########################################################
from app.ledger.repository.base import LedgerDBRepository


class MxTransactionDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID
    payment_account_id: str
    amount: int
    currency: str
    ledger_id: UUID
    idempotency_key: str
    target_type: str
    routing_key: datetime
    target_id: Optional[str]
    legacy_transaction_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    context: Optional[str] = None
    metadata: Optional[str] = None


class InsertMxTransactionInput(MxTransactionDbEntity):
    pass


class InsertMxTransactionOutput(MxTransactionDbEntity):
    pass


class MxTransactionRepositoryInterface:
    @abstractmethod
    async def insert_mx_transaction(
        self, request: InsertMxTransactionInput
    ) -> InsertMxTransactionOutput:
        ...


@dataclass
class MxTransactionRepository(MxTransactionRepositoryInterface, LedgerDBRepository):
    async def insert_mx_transaction(
        self, request: InsertMxTransactionInput
    ) -> InsertMxTransactionOutput:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            stmt = (
                mx_transactions.table.insert()
                .values(request.dict(skip_defaults=True))
                .returning(*mx_transactions.table.columns.values())
            )
            row = await conn.execution_options(
                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return InsertMxTransactionOutput.from_orm(row)
