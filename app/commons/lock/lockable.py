from abc import ABC, abstractmethod
from typing import Optional

from app.commons.lock.models import (
    LockRequest,
    UnlockRequest,
    GetLockRequest,
    LockInternal,
)


class Lockable(ABC):
    @abstractmethod
    async def lock(self, lock_request: LockRequest) -> Optional[LockInternal]:
        pass

    @abstractmethod
    async def unlock(self, unlock_request: UnlockRequest) -> Optional[LockInternal]:
        pass

    @abstractmethod
    async def get_lock(
        self, get_lock_request: GetLockRequest
    ) -> Optional[LockInternal]:
        pass
