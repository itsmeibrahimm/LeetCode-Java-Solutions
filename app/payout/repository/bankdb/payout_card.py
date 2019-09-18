from abc import ABC, abstractmethod
from typing import Optional, List

from sqlalchemy import desc
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model import payout_card
from app.payout.repository.bankdb.model.payout_card import PayoutCardCreate, PayoutCard


class PayoutCardRepositoryInterface(ABC):
    @abstractmethod
    async def create_payout_card(self, data: PayoutCardCreate) -> PayoutCard:
        pass

    @abstractmethod
    async def get_payout_card_by_id(self, payout_card_id: int) -> Optional[PayoutCard]:
        pass

    @abstractmethod
    async def list_payout_cards_by_ids(
        self, payout_card_id_list: List[int]
    ) -> List[PayoutCard]:
        pass


@final
@tracing.track_breadcrumb(repository_name="payout_card")
class PayoutCardRepository(PayoutBankDBRepository, PayoutCardRepositoryInterface):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_payout_card(self, data: PayoutCardCreate) -> PayoutCard:
        stmt = (
            payout_card.table.insert()
            .values(data.dict(skip_defaults=True))
            .returning(*payout_card.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return PayoutCard.from_row(row)

    async def get_payout_card_by_id(self, payout_card_id: int) -> Optional[PayoutCard]:
        stmt = payout_card.table.select().where(payout_card.id == payout_card_id)
        row = await self._database.replica().fetch_one(stmt)
        return PayoutCard.from_row(row) if row else None

    async def list_payout_cards_by_ids(
        self, payout_card_id_list: List[int]
    ) -> List[PayoutCard]:
        stmt = (
            payout_card.table.select()
            .order_by(desc(payout_card.id))  # set order_by pk desc as default for now
            .where(payout_card.id.in_(payout_card_id_list))
        )

        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            return [PayoutCard.from_row(row) for row in rows]
        else:
            return []
