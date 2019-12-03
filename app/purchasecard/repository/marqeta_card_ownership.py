from abc import abstractmethod, ABC
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, desc
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.maindb import marqeta_card_ownerships
from app.purchasecard.models.maindb.marqeta_card_ownership import MarqetaCardOwnership
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


class MarqetaCardOwnershipRepositoryInterface(ABC):
    @abstractmethod
    async def create_card_ownership(
        self, dasher_id: int, card_id: str
    ) -> MarqetaCardOwnership:
        pass

    @abstractmethod
    async def get_card_ownership_by_id(
        self, marqeta_card_ownership_id: int
    ) -> Optional[MarqetaCardOwnership]:
        pass

    @abstractmethod
    async def get_active_card_ownerships_by_card_id(
        self, card_id: str
    ) -> List[MarqetaCardOwnership]:
        pass

    @abstractmethod
    async def get_active_card_ownership_by_dasher_id(
        self, dasher_id: int
    ) -> Optional[MarqetaCardOwnership]:
        pass

    @abstractmethod
    async def update_card_ownership_ended_at(
        self, marqeta_card_ownership_id: int, ended_at: datetime
    ) -> Optional[MarqetaCardOwnership]:
        pass


@final
@tracing.track_breadcrumb(repository_name="marqeta_card_ownership")
class MarqetaCardOwnershipRepository(
    PurchaseCardMainDBRepository, MarqetaCardOwnershipRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_card_ownership(
        self, dasher_id: int, card_id: str
    ) -> MarqetaCardOwnership:
        stmt = (
            marqeta_card_ownerships.table.insert()
            .values(
                {
                    "dasher_id": dasher_id,
                    "card_id": card_id,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            .returning(*marqeta_card_ownerships.table.columns.values())
        )

        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return MarqetaCardOwnership.from_row(row)

    async def get_card_ownership_by_id(
        self, marqeta_card_ownership_id: int
    ) -> Optional[MarqetaCardOwnership]:
        stmt = marqeta_card_ownerships.table.select().where(
            marqeta_card_ownerships.id == marqeta_card_ownership_id
        )

        row = await self._database.replica().fetch_one(stmt)
        return MarqetaCardOwnership.from_row(row) if row else None

    async def get_active_card_ownerships_by_card_id(
        self, card_id: str
    ) -> List[MarqetaCardOwnership]:
        stmt = marqeta_card_ownerships.table.select().where(
            and_(
                marqeta_card_ownerships.card_id == card_id,
                marqeta_card_ownerships.ended_at.is_(None),
            )
        )

        rows = await self._database.replica().execute(stmt)
        return [MarqetaCardOwnership.from_row(row) for row in rows]

    async def get_active_card_ownership_by_dasher_id(
        self, dasher_id: int
    ) -> Optional[MarqetaCardOwnership]:
        stmt = (
            marqeta_card_ownerships.table.select()
            .order_by(desc(marqeta_card_ownerships.id))
            .where(
                and_(
                    marqeta_card_ownerships.dasher_id == dasher_id,
                    marqeta_card_ownerships.ended_at.is_(None),
                )
            )
        )

        row = await self._database.replica().fetch_one(stmt)
        return MarqetaCardOwnership.from_row(row) if row else None

    async def update_card_ownership_ended_at(
        self, marqeta_card_ownership_id: int, ended_at: datetime
    ) -> Optional[MarqetaCardOwnership]:
        stmt = (
            marqeta_card_ownerships.table.update()
            .where(marqeta_card_ownerships.id == marqeta_card_ownership_id)
            .values(ended_at=ended_at)
            .returning(*marqeta_card_ownerships.table.columns.values())
        )

        row = await self._database.master().fetch_one(stmt)
        return MarqetaCardOwnership.from_row(row) if row else None
