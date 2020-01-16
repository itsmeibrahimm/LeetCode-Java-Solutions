from abc import ABC, abstractmethod
from typing import Optional

from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.paymentdb.base import PayoutPaymentDBRepository
from app.payout.repository.paymentdb.model import payout_lock
from app.payout.repository.paymentdb.model.payout_lock import (
    PayoutLock,
    PayoutLockCreate,
)


class PayoutLockRepositoryInterface(ABC):
    @abstractmethod
    async def create_payout_lock(self, data: PayoutLockCreate) -> PayoutLock:
        pass

    @abstractmethod
    async def get_payout_lock(self, lock_id: str) -> Optional[PayoutLock]:
        pass


@final
@tracing.track_breadcrumb(repository_name="payout_lock")
class PayoutLockRepository(PayoutPaymentDBRepository, PayoutLockRepositoryInterface):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_payout_lock(self, data: PayoutLockCreate) -> PayoutLock:
        stmt = (
            payout_lock.table.insert()
            .values(data.dict(skip_defaults=True))
            .returning(*payout_lock.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return PayoutLock.from_row(row)

    async def get_payout_lock(self, lock_id: str) -> Optional[PayoutLock]:
        stmt = payout_lock.table.select().where(payout_lock.lock_id == lock_id)
        row = await self._database.replica().fetch_one(stmt)
        return PayoutLock.from_row(row) if row else None
