from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy import and_
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.maindb import marqeta_cards
from app.purchasecard.models.maindb.marqeta_card import MarqetaCard
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


class MarqetaCardRepositoryInterface(ABC):
    @abstractmethod
    async def get(
        self, *, token: str, delight_number: int, last4: str
    ) -> Optional[MarqetaCard]:
        pass

    @abstractmethod
    async def create(self, token: str, delight_number: int, last4: str) -> MarqetaCard:
        pass


@final
@tracing.track_breadcrumb(repository_name="marqeta_card")
class MarqetaCardRepository(
    PurchaseCardMainDBRepository, MarqetaCardRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def get(
        self, *, token: str, delight_number: int, last4: str
    ) -> Optional[MarqetaCard]:
        stmt = marqeta_cards.table.select().where(
            and_(
                marqeta_cards.token == token,
                marqeta_cards.delight_number == delight_number,
                marqeta_cards.last4 == last4,
            )
        )
        row = await self._database.replica().fetch_one(stmt)
        return MarqetaCard.from_row(row) if row else None

    async def create(self, token: str, delight_number: int, last4: str) -> MarqetaCard:
        data = {"token": token, "delight_number": delight_number, "last4": last4}
        stmt = (
            marqeta_cards.table.insert()
            .values(data)
            .returning(*marqeta_cards.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return MarqetaCard.from_row(row)
