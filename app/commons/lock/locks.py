from aioredlock import Aioredlock, LockError

from app.commons.context.logger import get_logger
from app.commons.core.errors import PaymentLockAcquireError, PaymentLockReleaseError

log = get_logger("application")


class PaymentLock:
    """Async Context Manager of Payment Lock.

    Distributed async redis lock, which set a ttl for input lock_name as key in redis. Example usage,

        async with PaymentLock(lock_name) as lock:
            # business logic under the lock
            pass

    If failed to acquire lock, will raise PaymentLockAcquireError.

    When lock timed out on exiting context manager, if there is another lock with same lock_name, it will raise
    PaymentLockReleaseError, otherwise, will succeed to release the lock.
    """

    def __init__(
        self,
        lock_name: str,
        redis_lock_manager: Aioredlock,
        lock_timeout: float = None,
        max_retry: int = None,
    ):
        """Init Payment Lock Context Manager.

        :param lock_name: name of the lock
        :param redis_lock_manager: redis lock manager
        :param lock_timeout: timeout for the lock, in seconds
        :param max_retry: max retry of the lock
        """
        self._resource = lock_name
        self._lock_manager = redis_lock_manager
        if lock_timeout is not None:
            self._lock_manager.redis.lock_timeout = lock_timeout
        if max_retry is not None:
            self._lock_manager.retry_count = max_retry
        self._lock = None

    async def __aenter__(self):
        """Acquire lock when enter."""
        try:
            self._lock = await self._lock_manager.lock(self._resource)
        except LockError as e:
            log.exception("LockError when attempting PaymentLock")
            raise PaymentLockAcquireError from e
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release lock when exit."""
        try:
            await self._lock_manager.unlock(self._lock)
        except LockError as e:
            raise PaymentLockReleaseError from e

    async def is_locked(self):
        """Check if resource is locked or not."""
        return await self._lock_manager.is_locked(self._lock)
