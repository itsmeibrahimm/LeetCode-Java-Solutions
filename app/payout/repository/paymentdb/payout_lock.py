from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import pytz
from sqlalchemy import and_

from app.commons import tracing
from app.commons.core.errors import PaymentDBLockReleaseError, PaymentDBLockAcquireError
from app.commons.database.infra import DB
from app.commons.lock.lockable import Lockable
from app.commons.lock.models import LockStatus, GetLockRequest, LockInternal
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


@dataclass
@tracing.track_breadcrumb(repository_name="payout_lock")
class PayoutLockRepository(
    PayoutPaymentDBRepository, PayoutLockRepositoryInterface, Lockable
):
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
        row = await self._database.master().fetch_one(stmt)
        return PayoutLock.from_row(row) if row else None

    async def lock(self, lock_request):
        async with self._database.master().connection().transaction() as tx:
            conn = tx.connection()

            stmt = (
                payout_lock.table.select()
                .where(payout_lock.lock_id == lock_request.lock_id)
                .with_for_update(nowait=True)
            )
            exist_row = await conn.fetch_one(stmt)
            # create lock row if it doesn't exist
            if not exist_row:
                await self.create_payout_lock(
                    PayoutLockCreate(lock_id=lock_request.lock_id)
                )
            else:
                # if there's an existing lock row, and it has been held for too long which exceed the lock_until time
                exist_lock = PayoutLock.from_row(exist_row)
                lock_until = exist_lock.lock_timestamp + timedelta(
                    seconds=exist_lock.ttl_sec
                )
                if exist_lock.status == LockStatus.LOCKED and datetime.now(
                    timezone.utc
                ) < lock_until.replace(tzinfo=pytz.UTC):
                    raise PaymentDBLockAcquireError

            # construct update request and update status, lock_timestamp, and ttl_sec
            update_stmt = (
                payout_lock.table.update()
                .where(payout_lock.lock_id == lock_request.lock_id)
                .values(
                    status=LockStatus.LOCKED,
                    lock_timestamp=datetime.now(timezone.utc),
                    ttl_sec=lock_request.ttl_sec,
                )
                .returning(*payout_lock.table.columns.values())
            )
            updated_row = await conn.fetch_one(update_stmt)
            assert updated_row
            lock = PayoutLock.from_row(updated_row)
            return LockInternal(**lock.dict())

    async def unlock(self, unlock_request):
        if not unlock_request.lock_internal:
            raise PaymentDBLockReleaseError

        async with self._database.master().connection().transaction() as tx:
            conn = tx.connection()
            # select for the same lock with lock_id, status, lock_timestamp and ttl_sec
            # if no row found, which means the row has been locked by other request
            # raise error for this case
            stmt = (
                payout_lock.table.select()
                .where(
                    and_(
                        payout_lock.lock_id == unlock_request.lock_internal.lock_id,
                        payout_lock.status == unlock_request.lock_internal.status,
                        payout_lock.lock_timestamp
                        == unlock_request.lock_internal.lock_timestamp,
                        payout_lock.ttl_sec == unlock_request.lock_internal.ttl_sec,
                    )
                )
                .with_for_update(nowait=True)
            )
            exist_lock = await conn.fetch_one(stmt)
            if not exist_lock:
                raise PaymentDBLockReleaseError

            # construct update request and update status
            update_stmt = (
                payout_lock.table.update()
                .where(payout_lock.lock_id == unlock_request.lock_internal.lock_id)
                .values(status=LockStatus.OPEN)
                .returning(*payout_lock.table.columns.values())
            )
            updated_row = await conn.fetch_one(update_stmt)
            assert updated_row
            lock = PayoutLock.from_row(updated_row)
            return LockInternal(**lock.dict())

    async def get_lock(
        self, get_lock_request: GetLockRequest
    ) -> Optional[LockInternal]:
        lock = await self.get_payout_lock(lock_id=get_lock_request.lock_id)
        if not lock:
            return None
        return LockInternal(**lock.dict())
