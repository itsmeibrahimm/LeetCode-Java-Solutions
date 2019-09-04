from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass

from app.commons import tracing
from app.ledger.core.data_types import (
    InsertMxScheduledLedgerInput,
    InsertMxScheduledLedgerOutput,
)
from app.ledger.models.paymentdb import mx_scheduled_ledgers
from app.ledger.repository.base import LedgerDBRepository


class MxScheduledLedgerRepositoryInterface:
    @abstractmethod
    async def insert_mx_scheduled_ledger(
        self, request: InsertMxScheduledLedgerInput
    ) -> InsertMxScheduledLedgerOutput:
        ...


@dataclass
@tracing.set_repository_name("mx_scheduled_ledger", only_trackable=False)
class MxScheduledLedgerRepository(
    MxScheduledLedgerRepositoryInterface, LedgerDBRepository
):
    async def insert_mx_scheduled_ledger(
        self, request: InsertMxScheduledLedgerInput
    ) -> InsertMxScheduledLedgerOutput:
        stmt = (
            mx_scheduled_ledgers.table.insert()
            .values(request.dict(skip_defaults=True))
            .returning(*mx_scheduled_ledgers.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        assert row
        return InsertMxScheduledLedgerOutput.from_row(row)
