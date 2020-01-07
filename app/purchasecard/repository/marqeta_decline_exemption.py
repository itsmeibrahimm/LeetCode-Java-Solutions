from abc import ABC, abstractmethod
from datetime import datetime, timezone

from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.maindb.marqeta_decline_exemption import (
    MarqetaDeclineExemption,
)
from app.purchasecard.models.maindb import marqeta_decline_exemptions
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


class MarqetaDeclineExemptionRepositoryInterface(ABC):
    @abstractmethod
    async def create(
        self, delivery_id: int, creator_id: int, amount: int, dasher_id: int, mid: str
    ) -> MarqetaDeclineExemption:
        pass


@final
@tracing.track_breadcrumb(repository_name="marqeta_decline_exemption")
class MarqetaDeclineExemptionRepository(
    PurchaseCardMainDBRepository, MarqetaDeclineExemptionRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create(
        self, delivery_id: int, creator_id: int, amount: int, dasher_id: int, mid: str
    ) -> MarqetaDeclineExemption:
        data = {
            "amount": amount,
            "created_by_id": creator_id,
            "delivery_id": delivery_id,
            "mid": mid,
            "dasher_id": dasher_id,
            "created_at": datetime.now(timezone.utc),
        }
        stmt = (
            marqeta_decline_exemptions.table.insert()
            .values(data)
            .returning(*marqeta_decline_exemptions.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return MarqetaDeclineExemption.from_row(row)
