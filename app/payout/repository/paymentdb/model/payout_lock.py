from dataclasses import dataclass

from sqlalchemy import Column, Text
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PayoutLockTable(TableDefinition):
    name: str = no_init_field("payout_lock")
    lock_id: Column = no_init_field(Column("lock_id", Text, primary_key=True))


class _PayoutLock(DBEntity):
    lock_id: str


class PayoutLock(_PayoutLock):
    pass


class PayoutLockCreate(_PayoutLock):
    pass
