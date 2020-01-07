from abc import ABC, abstractmethod
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.sql import text
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.maindb import delivery_funding
from app.purchasecard.models.maindb.delivery_funding import DeliveryFunding
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


class DeliveryFundingRepositoryInterface(ABC):
    @abstractmethod
    async def create(
        self, creator_id: int, delivery_id: int, swipe_amount: int
    ) -> DeliveryFunding:
        pass

    @abstractmethod
    async def get_total_funding_by_delivery_id(self, delivery_id: int) -> int:
        pass


@final
@tracing.track_breadcrumb(repository_name="delivery_funding")
class DeliveryFundingRepository(
    PurchaseCardMainDBRepository, DeliveryFundingRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def get_total_funding_by_delivery_id(self, delivery_id: int) -> int:
        stmt = (
            select([text("SUM(amount) as total_amount")])
            .where(delivery_funding.delivery_id == delivery_id)
            .group_by(delivery_funding.delivery_id)
        )

        row = await self._database.replica().fetch_one(stmt)
        if not row:
            return 0
        # sqlalchemy would return a tuple here
        return row._row_proxy[0]  # type: ignore

    async def create(
        self, creator_id: int, delivery_id: int, swipe_amount: int
    ) -> DeliveryFunding:
        data = {
            "amount": swipe_amount,
            "created_by_id": creator_id,
            "delivery_id": delivery_id,
            "created_at": datetime.now(timezone.utc),
        }
        stmt = (
            delivery_funding.table.insert()
            .values(data)
            .returning(*delivery_funding.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return DeliveryFunding.from_row(row)
