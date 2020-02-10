from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text, and_
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.maindb import card_acceptors
from app.purchasecard.models.maindb.card_acceptor import CardAcceptor
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


class CardAcceptorRepositoryInterface(ABC):
    @abstractmethod
    async def get_card_acceptor_by_id(
        self, card_acceptor_id: int
    ) -> Optional[CardAcceptor]:
        pass

    @abstractmethod
    async def get_card_acceptor_by_card_acceptor_info(
        self, mid: str, name: str, city: str, zip_code: str, state: str
    ) -> Optional[CardAcceptor]:
        pass

    @abstractmethod
    async def create_card_acceptor(
        self,
        mid: str,
        name: str,
        city: str,
        zip_code: str,
        state: str,
        should_be_examined: Optional[bool] = False,
    ) -> CardAcceptor:
        pass

    @abstractmethod
    async def get_or_create_card_acceptor(
        self,
        mid: str,
        name: str,
        city: str,
        zip_code: str,
        state: str,
        should_be_examined: Optional[bool] = False,
    ) -> CardAcceptor:
        pass

    @abstractmethod
    async def update_card_acceptor(
        self, card_acceptor_id: int, should_be_examined: bool
    ) -> CardAcceptor:
        pass


@final
@tracing.track_breadcrumb(repository_name="card_acceptor")
class CardAcceptorRepository(
    PurchaseCardMainDBRepository, CardAcceptorRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def get_card_acceptor_by_id(
        self, card_acceptor_id: int
    ) -> Optional[CardAcceptor]:
        stmt = select([text("*")]).where(and_(card_acceptors.id == card_acceptor_id))
        result = await self._database.replica().fetch_one(stmt)
        return CardAcceptor.from_row(result) if result else None

    async def get_card_acceptor_by_card_acceptor_info(
        self, mid: str, name: str, city: str, zip_code: str, state: str
    ) -> Optional[CardAcceptor]:
        stmt = select([text("*")]).where(
            and_(
                card_acceptors.mid == mid,
                card_acceptors.card_acceptor_name == name,
                card_acceptors.city == city,
                card_acceptors.zip_code == zip_code,
                card_acceptors.state == state,
            )
        )
        result = await self._database.replica().fetch_one(stmt)
        return CardAcceptor.from_row(result) if result else None

    async def create_card_acceptor(
        self,
        mid: str,
        name: str,
        city: str,
        zip_code: str,
        state: str,
        should_be_examined: Optional[bool] = False,
    ) -> CardAcceptor:
        now = datetime.now(timezone.utc)
        stmt = (
            card_acceptors.table.insert()
            .values(
                {
                    "mid": mid,
                    "created_at": now,
                    "name": name,
                    "city": city,
                    "state": state,
                    "zip_code": zip_code,
                    "is_blacklisted": False,
                    "should_be_examined": should_be_examined,
                }
            )
            .returning(*card_acceptors.table.columns.values())
        )
        result = await self._database.master().fetch_one(stmt)
        assert result
        return CardAcceptor.from_row(result)

    async def get_or_create_card_acceptor(
        self,
        mid: str,
        name: str,
        city: str,
        zip_code: str,
        state: str,
        should_be_examined: Optional[bool] = False,
    ):
        card_acceptor = await self.get_card_acceptor_by_card_acceptor_info(
            mid=mid, name=name, city=city, zip_code=zip_code, state=state
        )
        if not card_acceptor:
            return self.create_card_acceptor(
                mid=mid,
                name=name,
                city=city,
                zip_code=zip_code,
                state=state,
                should_be_examined=should_be_examined,
            )
        return card_acceptor

    async def update_card_acceptor(
        self, card_acceptor_id: int, should_be_examined: bool
    ) -> CardAcceptor:
        stmt = (
            card_acceptors.table.update()
            .where(card_acceptors.id == card_acceptor_id)
            .values({"should_be_examined": should_be_examined})
            .returning(*card_acceptors.table.columns.values())
        )
        result = await self._database.master().fetch_one(stmt)
        return CardAcceptor.from_row(result) if result else None
