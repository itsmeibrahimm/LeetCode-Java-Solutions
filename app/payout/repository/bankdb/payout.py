from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model.payout import Payout, PayoutCreate, PayoutUpdate
from app.payout.repository.bankdb.model import payouts


class PayoutRepositoryInterface(ABC):
    @abstractmethod
    async def create_payout(self, data: PayoutCreate) -> Payout:
        pass

    @abstractmethod
    async def get_payout_by_id(self, payout_id: int) -> Optional[Payout]:
        pass

    @abstractmethod
    async def update_payout_by_id(
        self, payout_id: int, data: PayoutUpdate
    ) -> Optional[Payout]:
        pass


@final
@tracing.track_breadcrumb(repository_name="payout")
class PayoutRepository(PayoutBankDBRepository, PayoutRepositoryInterface):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_payout(self, data: PayoutCreate) -> Payout:
        ts_now = datetime.utcnow()
        stmt = (
            payouts.table.insert()
            .values(data.dict(skip_defaults=True), created_at=ts_now, updated_at=ts_now)
            .returning(*payouts.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return Payout.from_row(row)

    async def get_payout_by_id(self, payout_id: int) -> Optional[Payout]:
        stmt = payouts.table.select().where(payouts.id == payout_id)
        row = await self._database.replica().fetch_one(stmt)
        return Payout.from_row(row) if row else None

    async def update_payout_by_id(
        self, payout_id: int, data: PayoutUpdate
    ) -> Optional[Payout]:
        stmt = (
            payouts.table.update()
            .where(payouts.id == payout_id)
            .values(
                data.dict_after_json_to_string(skip_defaults=True),
                updated_at=datetime.utcnow(),
            )
            .returning(*payouts.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return Payout.from_row(row) if row else None
