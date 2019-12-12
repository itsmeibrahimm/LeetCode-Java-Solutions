from sqlalchemy import select
from sqlalchemy.sql import text
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.maindb import delivery_funding
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


@final
@tracing.track_breadcrumb(repository_name="delivery_funding")
class DeliveryFundingRepository(PurchaseCardMainDBRepository):
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
