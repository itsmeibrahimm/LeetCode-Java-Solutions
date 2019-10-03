from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass

from app.commons import tracing
from app.commons.database.infra import DB
from app.ledger.core.data_types import (
    InsertMxScheduledLedgerInput,
    InsertMxScheduledLedgerOutput,
)
from app.ledger.models.paymentdb import mx_scheduled_ledgers
from app.ledger.repository.base import LedgerPaymentDBRepository


class MxScheduledLedgerRepositoryInterface:
    @abstractmethod
    async def insert_mx_scheduled_ledger(
        self, request: InsertMxScheduledLedgerInput
    ) -> InsertMxScheduledLedgerOutput:
        ...


@tracing.track_breadcrumb(repository_name="mx_scheduled_ledger")
@dataclass
class MxScheduledLedgerRepository(
    MxScheduledLedgerRepositoryInterface, LedgerPaymentDBRepository
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def insert_mx_scheduled_ledger(
        self, request: InsertMxScheduledLedgerInput
    ) -> InsertMxScheduledLedgerOutput:
        stmt = (
            mx_scheduled_ledgers.table.insert()
            .values(request.dict(skip_defaults=True))
            .returning(*mx_scheduled_ledgers.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row
        return InsertMxScheduledLedgerOutput.from_row(row)
