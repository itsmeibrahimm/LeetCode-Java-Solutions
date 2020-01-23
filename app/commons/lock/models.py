from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.commons.database.model import DBEntity


class LockStatus(str, Enum):
    OPEN = "open"
    LOCKED = "locked"


class LockInternal(BaseModel):
    lock_id: str
    status: Optional[LockStatus]
    lock_timestamp: Optional[datetime]
    ttl_sec: Optional[int]


class LockRequest(DBEntity):
    lock_id: str
    ttl_sec: int


class UnlockRequest(DBEntity):
    lock_internal: LockInternal


class GetLockRequest(DBEntity):
    lock_id: str
