import json
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from sqlalchemy import select, text
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.constants import MARQETA_TRANSACTION_EVENT_TRANSACTION_TYPE
from app.purchasecard.models.maindb import marqeta_transaction_events
from app.purchasecard.models.maindb.marqeta_transaction_event import (
    MarqetaTransactionEvent,
)
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


class MarqetaTransactionEventRepositoryInterface(ABC):
    @abstractmethod
    async def get_transaction_event_by_token(
        self, transaction_token: str
    ) -> Optional[MarqetaTransactionEvent]:
        pass

    @abstractmethod
    async def has_transaction_event_for_token(self, transaction_token: str) -> bool:
        pass

    @abstractmethod
    async def create_transaction_event(
        self,
        token: str,
        amount: int,
        metadata: Dict[str, Any],
        raw_type: str,
        ownership_id: int,
        shift_id: Optional[int] = None,
        card_acceptor_id: Optional[int] = None,
    ) -> MarqetaTransactionEvent:
        pass


@final
@tracing.track_breadcrumb(repository_name="marqeta_transaction_event")
class MarqetaTransactionEventRepository(
    PurchaseCardMainDBRepository, MarqetaTransactionEventRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def get_transaction_event_by_token(
        self, transaction_token: str
    ) -> Optional[MarqetaTransactionEvent]:
        stmt = select([text("*")]).where(
            marqeta_transaction_events.token == transaction_token
        )
        result = await self._database.replica().fetch_one(stmt)
        return MarqetaTransactionEvent.from_row(result) if result else None

    async def has_transaction_event_for_token(self, transaction_token: str) -> bool:
        stmt = select([text("count(*)")]).where(
            marqeta_transaction_events.token == transaction_token
        )
        result = await self._database.replica().fetch_value(stmt)
        return True if result else False

    async def create_transaction_event(
        self,
        token: str,
        amount: int,
        metadata: Dict[str, Any],
        raw_type: str,
        ownership_id: int,
        shift_id: Optional[int] = None,
        card_acceptor_id: Optional[int] = None,
    ) -> MarqetaTransactionEvent:
        now = datetime.now(timezone.utc)
        stmt = (
            marqeta_transaction_events.table.insert()
            .values(
                {
                    "token": token,
                    "created_at": now,
                    "metadata": json.dumps(metadata),
                    "raw_type": raw_type,
                    "ownership_id": ownership_id,
                    "transaction_type": MARQETA_TRANSACTION_EVENT_TRANSACTION_TYPE,
                    "shift_id": shift_id,
                    "card_acceptor_id": card_acceptor_id,
                    "amount": amount,
                }
            )
            .returning(*marqeta_transaction_events.table.columns.values())
        )
        result = await self._database.master().fetch_one(stmt)
        assert result
        return MarqetaTransactionEvent.from_row(result)
