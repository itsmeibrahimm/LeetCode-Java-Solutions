from app.commons.constants import DEFAULT_TTL_SEC
from app.commons.context.logger import get_logger
from app.commons.core.errors import PaymentDBLockAcquireError, PaymentDBLockReleaseError
from app.commons.lock.lockable import Lockable
from app.commons.lock.models import GetLockRequest, LockStatus
from app.payout.repository.paymentdb.model.payout_lock import (
    PayoutLockRequest,
    PayoutUnlockRequest,
)

log = get_logger("application")


class PaymentDBLock:
    """Async Context Manager of Payout Lock.
    """

    def __init__(
        self, lockable_db: Lockable, lock_id: str, ttl_sec: int = DEFAULT_TTL_SEC
    ):
        """Init Payout Lock Context Manager.

        :param lockable_db: a repository class object which implements lockable
        :param lock_id: unique id of the lock
        """
        self._lockable_db = lockable_db
        self._lock_id = lock_id
        self._ttl_sec = ttl_sec

    async def __aenter__(self):
        """Acquire lock when enter."""
        try:
            internal_lock = await self._lockable_db.lock(
                PayoutLockRequest(lock_id=self._lock_id, ttl_sec=self._ttl_sec)
            )
            self._lock_on_hold = internal_lock
        except Exception as e:
            log.exception("Error when attempting lock")
            raise PaymentDBLockAcquireError from e
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release lock when exit."""
        try:
            await self._lockable_db.unlock(
                PayoutUnlockRequest(lock_internal=self._lock_on_hold)
            )
        except Exception as e:
            log.exception("Error when releasing lock")
            raise PaymentDBLockReleaseError from e

    async def is_locked(self) -> bool:
        """Check if resource is locked or not."""
        internal_lock = await self._lockable_db.get_lock(
            GetLockRequest(lock_id=self._lock_id)
        )
        if internal_lock and internal_lock.status == LockStatus.LOCKED:
            return True
        return False
