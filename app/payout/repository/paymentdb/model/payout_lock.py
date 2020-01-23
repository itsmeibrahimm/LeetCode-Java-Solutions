from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text, DateTime, Integer
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.lock.models import LockRequest, UnlockRequest
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PayoutLockTable(TableDefinition):
    name: str = no_init_field("payout_lock")
    lock_id: Column = no_init_field(Column("lock_id", Text, primary_key=True))
    status: Column = no_init_field(Column("status", Text))
    lock_timestamp: Column = no_init_field(Column("lock_timestamp", DateTime(True)))
    ttl_sec: Column = no_init_field(Column("ttl_sec", Integer))


class _PayoutLock(DBEntity):
    lock_id: str


class PayoutLock(_PayoutLock):
    lock_id: str
    status: Optional[str]
    lock_timestamp: Optional[datetime]
    ttl_sec: Optional[int]


class PayoutLockCreate(_PayoutLock):
    lock_id: str


class PayoutLockRequest(LockRequest):
    pass


class PayoutUnlockRequest(UnlockRequest):
    pass
