from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from sqlalchemy import and_
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.maindb import marqeta_card_transitions
from app.purchasecard.models.maindb.marqeta_card_transition import (
    MarqetaCardTransition,
    TransitionState,
)
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


class MarqetaCardTransitionRepositoryInterface(ABC):
    @abstractmethod
    async def create_transition(
        self, card_id: str, desired_state: TransitionState, shift_id=None
    ) -> MarqetaCardTransition:
        pass

    @abstractmethod
    async def get_failed_transitions(self, card_id: str) -> List[MarqetaCardTransition]:
        pass

    @abstractmethod
    async def update_transitions_aborted_at(
        self, transition_ids: List[int], aborted_at: datetime
    ) -> List[MarqetaCardTransition]:
        pass

    @abstractmethod
    async def update_transitions_succeeded_at(
        self, transition_ids: List[int], succeeded_at: datetime
    ) -> List[MarqetaCardTransition]:
        pass


@final
@tracing.track_breadcrumb(repository_name="marqeta_card_transition")
class MarqetaCardTransitionRepository(
    PurchaseCardMainDBRepository, MarqetaCardTransitionRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_transition(
        self, card_id: str, desired_state: TransitionState, shift_id: int = None
    ) -> MarqetaCardTransition:
        stmt = (
            marqeta_card_transitions.table.insert()
            .values(
                created_at=datetime.utcnow(),
                card_id=card_id,
                desired_state=desired_state,
                shift_id=shift_id,
            )
            .returning(*marqeta_card_transitions.table.columns.values())
        )

        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return MarqetaCardTransition.from_row(row)

    async def get_failed_transitions(self, card_id: str) -> List[MarqetaCardTransition]:
        stmt = marqeta_card_transitions.table.select().where(
            and_(
                marqeta_card_transitions.card_id == card_id,
                marqeta_card_transitions.succeeded_at.is_(None),
                marqeta_card_transitions.aborted_at.is_(None),
            )
        )

        rows = await self._database.replica().fetch_all(stmt)
        return [MarqetaCardTransition.from_row(row) for row in rows]

    async def update_transitions_aborted_at(
        self, transition_ids: List[int], aborted_at: datetime
    ) -> List[MarqetaCardTransition]:
        stmt = (
            marqeta_card_transitions.table.update()
            .where(marqeta_card_transitions.id.in_(transition_ids))
            .values(aborted_at=aborted_at)
            .returning(*marqeta_card_transitions.table.columns.values())
        )

        rows = await self._database.master().fetch_all(stmt)
        return [MarqetaCardTransition.from_row(row) for row in rows]

    async def update_transitions_succeeded_at(
        self, transition_ids: List[int], succeeded_at: datetime
    ) -> List[MarqetaCardTransition]:
        stmt = (
            marqeta_card_transitions.table.update()
            .where(marqeta_card_transitions.id.in_(transition_ids))
            .values(succeeded_at=succeeded_at)
            .returning(*marqeta_card_transitions.table.columns.values())
        )

        rows = await self._database.master().fetch_all(stmt)
        return [MarqetaCardTransition.from_row(row) for row in rows]
