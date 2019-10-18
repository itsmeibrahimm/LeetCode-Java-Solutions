from abc import ABC, abstractmethod
from datetime import datetime
from operator import attrgetter
from typing import Optional, List

from sqlalchemy import and_, desc, or_
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model import transactions
from app.payout.repository.bankdb.model.transaction import (
    TransactionDBEntity,
    TransactionCreateDBEntity,
    TransactionUpdateDBEntity,
)
from app.payout.types import TransactionState


class TransactionRepositoryInterface(ABC):
    @abstractmethod
    async def create_transaction(
        self, data: TransactionCreateDBEntity
    ) -> TransactionDBEntity:
        pass

    @abstractmethod
    async def get_transaction_by_id(
        self, transaction_id: int
    ) -> Optional[TransactionDBEntity]:
        pass

    @abstractmethod
    async def get_transaction_by_ids(
        self, transaction_ids: List[int]
    ) -> List[TransactionDBEntity]:
        pass

    @abstractmethod
    async def get_transaction_by_target_ids_and_type(
        self, target_ids: List[int], target_type: str, offset: int, limit: int
    ) -> List[TransactionDBEntity]:
        pass

    @abstractmethod
    async def get_transaction_by_transfer_id(
        self, transfer_id: int, offset: int, limit: int
    ) -> List[TransactionDBEntity]:
        pass

    @abstractmethod
    async def get_transaction_by_payout_id(
        self, payout_id: int, offset: int, limit: int
    ) -> List[TransactionDBEntity]:
        pass

    @abstractmethod
    async def get_transaction_by_payout_account_id(
        self,
        payout_account_id: int,
        offset: int,
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TransactionDBEntity]:
        pass

    @abstractmethod
    async def get_unpaid_transaction_by_payout_account_id(
        self,
        payout_account_id: int,
        offset: int,
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TransactionDBEntity]:
        pass

    @abstractmethod
    async def get_unpaid_transaction(
        self,
        offset: int,
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TransactionDBEntity]:
        pass

    @abstractmethod
    async def update_transaction_by_id(
        self, transaction_id: int, data: TransactionUpdateDBEntity
    ) -> Optional[TransactionDBEntity]:
        pass

    @abstractmethod
    async def set_transaction_payout_id_by_ids(
        self, transaction_ids: List[int], payout_id: Optional[int] = None
    ) -> List[TransactionDBEntity]:
        pass


@final
@tracing.track_breadcrumb(repository_name="transaction")
class TransactionRepository(PayoutBankDBRepository, TransactionRepositoryInterface):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_transaction(
        self, data: TransactionCreateDBEntity
    ) -> TransactionDBEntity:
        ts_now = datetime.utcnow()
        stmt = (
            transactions.table.insert()
            .values(data.dict(skip_defaults=True), created_at=ts_now, updated_at=ts_now)
            .returning(*transactions.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return TransactionDBEntity.from_row(row)

    async def get_transaction_by_id(
        self, transaction_id: int
    ) -> Optional[TransactionDBEntity]:
        stmt = transactions.table.select().where(transactions.id == transaction_id)
        row = await self._database.replica().fetch_one(stmt)
        return TransactionDBEntity.from_row(row) if row else None

    async def update_transaction_by_id(
        self, transaction_id: int, data: TransactionUpdateDBEntity
    ) -> Optional[TransactionDBEntity]:
        stmt = (
            transactions.table.update()
            .where(transactions.id == transaction_id)
            .values(data.dict(skip_defaults=True), updated_at=datetime.utcnow())
            .returning(*transactions.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return TransactionDBEntity.from_row(row) if row else None

    async def set_transaction_payout_id_by_ids(
        self, transaction_ids: List[int], payout_id: Optional[int] = None
    ) -> List[TransactionDBEntity]:
        stmt = (
            transactions.table.update()
            .where(transactions.id.in_(transaction_ids))
            .values(payout_id=payout_id, updated_at=datetime.utcnow())
            .returning(*transactions.table.columns.values())
        )
        rows = await self._database.master().fetch_all(stmt)
        results = [TransactionDBEntity.from_row(row) for row in rows] if rows else []
        sorted_results = sorted(results, key=attrgetter("created_at"), reverse=True)
        return sorted_results

    async def get_transaction_by_ids(
        self, transaction_ids: List[int]
    ) -> List[TransactionDBEntity]:
        stmt = (
            transactions.table.select()
            .where(transactions.id.in_(transaction_ids))
            .order_by(desc(transactions.created_at))
        )

        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            return [TransactionDBEntity.from_row(row) for row in rows]
        else:
            return []

    async def get_transaction_by_target_ids_and_type(
        self, target_ids: List[int], target_type: str, offset: int, limit: int
    ) -> List[TransactionDBEntity]:
        stmt = (
            transactions.table.select()
            .where(
                and_(
                    transactions.target_id.in_(target_ids),
                    transactions.target_type == target_type,
                )
            )
            .order_by(desc(transactions.created_at))
            .offset(offset)
            .limit(limit)
        )

        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            return [TransactionDBEntity.from_row(row) for row in rows]
        else:
            return []

    async def get_transaction_by_transfer_id(
        self, transfer_id: int, offset: int, limit: int
    ) -> List[TransactionDBEntity]:
        stmt = (
            transactions.table.select()
            .where(transactions.transfer_id == transfer_id)
            .order_by(desc(transactions.created_at))
            .offset(offset)
            .limit(limit)
        )

        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            return [TransactionDBEntity.from_row(row) for row in rows]
        else:
            return []

    async def get_transaction_by_payout_id(
        self, payout_id: int, offset: int, limit: int
    ) -> List[TransactionDBEntity]:
        stmt = (
            transactions.table.select()
            .where(transactions.payout_id == payout_id)
            .order_by(desc(transactions.created_at))
            .offset(offset)
            .limit(limit)
        )

        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            return [TransactionDBEntity.from_row(row) for row in rows]
        else:
            return []

    async def get_transaction_by_payout_account_id(
        self,
        payout_account_id: int,
        offset: int,
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TransactionDBEntity]:
        and_statement = and_(
            # this line is necessary to make a valid and_statement, otherwise it will raise AttributeError
            transactions.payment_account_id.isnot(None),
            transactions.payment_account_id == payout_account_id,
        )
        if start_time:
            and_statement.clauses.append(transactions.created_at.__ge__(start_time))
        if end_time:
            and_statement.clauses.append(transactions.created_at.__le__(end_time))

        stmt = (
            transactions.table.select()
            .where(and_statement)
            .order_by(desc(transactions.created_at))
            .offset(offset)
            .limit(limit)
        )
        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            return [TransactionDBEntity.from_row(row) for row in rows]
        else:
            return []

    async def get_unpaid_transaction_by_payout_account_id(
        self,
        payout_account_id: int,
        offset: int,
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TransactionDBEntity]:
        and_statement = and_(
            transactions.payment_account_id == payout_account_id,
            transactions.transfer_id.is_(None),
            transactions.payout_id.is_(None),
            or_(
                transactions.state.is_(None),
                transactions.state == TransactionState.ACTIVE.value,
            ),
        )
        if start_time:
            and_statement.clauses.append(transactions.created_at.__ge__(start_time))
        if end_time:
            and_statement.clauses.append(transactions.created_at.__le__(end_time))
        stmt = (
            transactions.table.select()
            .where(and_statement)
            .order_by(desc(transactions.created_at))
            .offset(offset)
            .limit(limit)
        )
        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            return [TransactionDBEntity.from_row(row) for row in rows]
        else:
            return []

    async def get_unpaid_transaction(
        self,
        offset: int,
        limit: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TransactionDBEntity]:
        and_statement = and_(
            transactions.transfer_id.is_(None),
            transactions.payout_id.is_(None),
            or_(
                transactions.state.is_(None),
                transactions.state == TransactionState.ACTIVE.value,
            ),
        )
        if start_time:
            and_statement.clauses.append(transactions.created_at.__ge__(start_time))
        if end_time:
            and_statement.clauses.append(transactions.created_at.__le__(end_time))
        stmt = (
            transactions.table.select()
            .where(and_statement)
            .order_by(desc(transactions.created_at))
            .offset(offset)
            .limit(limit)
        )
        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            return [TransactionDBEntity.from_row(row) for row in rows]
        else:
            return []
