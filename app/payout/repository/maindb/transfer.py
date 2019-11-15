from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy import and_, desc
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.models import TransferMethodType
from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model import transfers, stripe_transfers
from app.payout.repository.maindb.model.transfer import (
    Transfer,
    TransferCreate,
    TransferUpdate,
    TransferStatus,
)


class TransferRepositoryInterface(ABC):
    @abstractmethod
    async def create_transfer(self, data: TransferCreate) -> Transfer:
        pass

    @abstractmethod
    async def get_transfer_by_id(self, transfer_id: int) -> Optional[Transfer]:
        pass

    @abstractmethod
    async def update_transfer_by_id(
        self, transfer_id: int, data: TransferUpdate
    ) -> Optional[Transfer]:
        pass

    @abstractmethod
    async def get_transfers_by_ids(self, transfer_ids: List[int]) -> List[Transfer]:
        pass

    @abstractmethod
    async def get_transfers_by_submitted_at_and_method(
        self, start_time: datetime
    ) -> List[int]:
        pass

    @abstractmethod
    async def get_unsubmitted_transfer_ids(self, created_before: datetime) -> List[int]:
        pass

    @abstractmethod
    async def get_transfers_by_payment_account_ids_and_count(
        self, payment_account_ids: List[int], offset: int, limit: int
    ) -> Tuple[List[Transfer], int]:
        pass

    @abstractmethod
    async def get_transfers_and_count_by_status_and_time_range(
        self,
        has_positive_amount: bool,
        offset: int,
        limit: int,
        status: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> Tuple[List[Transfer], int]:
        pass

    @abstractmethod
    async def get_positive_amount_transfers_and_count_by_time_range(
        self,
        offset: int,
        limit: int,
        is_submitted: bool,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> Tuple[List[Transfer], int]:
        pass


@final
@tracing.track_breadcrumb(repository_name="transfer")
class TransferRepository(PayoutMainDBRepository, TransferRepositoryInterface):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_transfer(self, data: TransferCreate) -> Transfer:
        stmt = (
            transfers.table.insert()
            .values(
                data.dict(skip_defaults=True), created_at=datetime.now(timezone.utc)
            )
            .returning(*transfers.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return Transfer.from_row(row)

    async def get_transfer_by_id(self, transfer_id: int) -> Optional[Transfer]:
        stmt = transfers.table.select().where(transfers.id == transfer_id)
        row = await self._database.replica().fetch_one(stmt)
        return Transfer.from_row(row) if row else None

    async def get_transfers_by_ids(self, transfer_ids: List[int]) -> List[Transfer]:
        stmt = transfers.table.select().where(transfers.id.in_(transfer_ids))
        rows = await self._database.replica().fetch_all(stmt)
        results = [Transfer.from_row(row) for row in rows] if rows else []
        return results

    async def get_transfers_by_submitted_at_and_method(
        self, start_time: datetime
    ) -> List[int]:
        override_stmt_timeout_in_ms = 10000
        query = and_(
            transfers.submitted_at.__ge__(start_time),
            transfers.method == TransferMethodType.STRIPE,
        )
        get_transfers_stmt = transfers.table.select().where(query)
        override_stmt_timeout_stmt = "SET LOCAL statement_timeout = {};".format(
            override_stmt_timeout_in_ms
        )
        async with self._database.replica().transaction() as transaction:
            await transaction.connection().execute(override_stmt_timeout_stmt)
            rows = await transaction.connection().fetch_all(get_transfers_stmt)

        if rows:
            results = [Transfer.from_row(row) for row in rows]
            return [transfer.id for transfer in results]
        else:
            return []

    async def get_transfers_by_payment_account_ids_and_count(
        self, payment_account_ids: List[int], offset: int, limit: int
    ) -> Tuple[List[Transfer], int]:
        query = and_(
            transfers.payment_account_id.isnot(None),
            transfers.payment_account_id.in_(payment_account_ids),
        )
        get_transfers_stmt = (
            transfers.table.select()
            .where(query)
            .order_by(desc(transfers.id))
            .offset(offset)
            .limit(limit)
        )
        rows = await self._database.replica().fetch_all(get_transfers_stmt)
        results = [Transfer.from_row(row) for row in rows] if rows else []

        count_stmt = transfers.table.count().where(query)
        count = 0
        count_fetched = await self._database.replica().fetch_value(count_stmt)
        if count_fetched:
            count = count_fetched
        return results, int(count)

    async def get_unsubmitted_transfer_ids(self, created_before: datetime) -> List[int]:
        query = and_(
            transfers.created_at.__lt__(created_before),
            transfers.amount.__gt__(0),
            transfers.status == TransferStatus.NEW,
        )
        stmt = transfers.table.select().where(query)
        rows = await self._database.replica().fetch_all(stmt)

        if rows:
            results = [Transfer.from_row(row) for row in rows]
            return [transfer.id for transfer in results]
        else:
            return []

    async def get_transfers_and_count_by_status_and_time_range(
        self,
        has_positive_amount: bool,
        offset: int,
        limit: int,
        status: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> Tuple[List[Transfer], int]:
        query = and_(transfers.status.isnot(None), transfers.status == status)
        if has_positive_amount:
            query.clauses.append(transfers.amount.__gt__(0))
        if start_time:
            query.clauses.append(transfers.created_at.__gt__(start_time))
        if end_time:
            query.clauses.append(transfers.created_at.__lt__(end_time))

        get_transfers_stmt = (
            transfers.table.select()
            .where(query)
            .order_by(desc(transfers.id))
            .offset(offset)
            .limit(limit)
        )
        rows = await self._database.replica().fetch_all(get_transfers_stmt)
        results = [Transfer.from_row(row) for row in rows] if rows else []

        count_stmt = transfers.table.count().where(query)
        count = 0
        count_fetched = await self._database.replica().fetch_value(count_stmt)
        if count_fetched:
            count = count_fetched
        return results, int(count)

    async def get_positive_amount_transfers_and_count_by_time_range(
        self,
        offset: int,
        limit: int,
        is_submitted: bool,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> Tuple[List[Transfer], int]:
        query = and_(transfers.amount.isnot(None), transfers.amount.__gt__(0))
        if is_submitted:
            query.clauses.append(stripe_transfers.table.c.transfer_id == transfers.id)
        if start_time:
            query.clauses.append(transfers.created_at.__gt__(start_time))
        if end_time:
            query.clauses.append(transfers.created_at.__lt__(end_time))

        get_transfers_stmt = (
            transfers.table.select()
            .where(query)
            .order_by(desc(transfers.id))
            .offset(offset)
            .limit(limit)
        )
        rows = await self._database.replica().fetch_all(get_transfers_stmt)
        results = [Transfer.from_row(row) for row in rows] if rows else []

        count_stmt = transfers.table.count().where(query)
        count = 0
        count_fetched = await self._database.replica().fetch_value(count_stmt)
        if count_fetched:
            count = count_fetched
        return results, int(count)

    async def update_transfer_by_id(
        self, transfer_id: int, data: TransferUpdate
    ) -> Optional[Transfer]:
        stmt = (
            transfers.table.update()
            .where(transfers.id == transfer_id)
            .values(data.dict(skip_defaults=True))
            .returning(*transfers.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return Transfer.from_row(row) if row else None
