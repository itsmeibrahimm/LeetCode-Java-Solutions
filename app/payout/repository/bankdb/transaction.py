from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model import transactions
from app.payout.repository.bankdb.model.transaction import (
    Transaction,
    TransactionCreate,
    TransactionUpdate,
)


class TransactionRepositoryInterface(ABC):
    @abstractmethod
    async def create_transaction(self, data: TransactionCreate) -> Transaction:
        pass

    @abstractmethod
    async def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        pass

    @abstractmethod
    async def update_transaction_by_id(
        self, transaction_id: int, data: TransactionUpdate
    ) -> Optional[Transaction]:
        pass

    @abstractmethod
    async def set_transaction_payout_id_by_ids(
        self, transaction_ids: List[int], data: TransactionUpdate
    ) -> List[Transaction]:
        pass


@final
@tracing.track_breadcrumb(repository_name="transaction")
class TransactionRepository(PayoutBankDBRepository, TransactionRepositoryInterface):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_transaction(self, data: TransactionCreate) -> Transaction:
        ts_now = datetime.utcnow()
        stmt = (
            transactions.table.insert()
            .values(data.dict(skip_defaults=True), created_at=ts_now, updated_at=ts_now)
            .returning(*transactions.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return Transaction.from_row(row)

    async def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        stmt = transactions.table.select().where(transactions.id == transaction_id)
        row = await self._database.replica().fetch_one(stmt)
        return Transaction.from_row(row) if row else None

    async def update_transaction_by_id(
        self, transaction_id: int, data: TransactionUpdate
    ) -> Optional[Transaction]:
        stmt = (
            transactions.table.update()
            .where(transactions.id == transaction_id)
            .values(data.dict(skip_defaults=True), updated_at=datetime.utcnow())
            .returning(*transactions.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return Transaction.from_row(row) if row else None

    async def set_transaction_payout_id_by_ids(
        self, transaction_ids: List[int], data: TransactionUpdate
    ) -> List[Transaction]:
        stmt = (
            transactions.table.update()
            .where(transactions.id.in_(transaction_ids))
            .values(data.dict(skip_defaults=True), updated_at=datetime.utcnow())
            .returning(*transactions.table.columns.values())
        )
        rows = await self._database.master().fetch_all(stmt)
        return [Transaction.from_row(row) for row in rows] if rows else []
