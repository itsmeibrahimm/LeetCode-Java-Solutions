from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model import stripe_payout_requests
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequest,
    StripePayoutRequestCreate,
    StripePayoutRequestUpdate,
)


class StripePayoutRequestRepositoryInterface(ABC):
    @abstractmethod
    async def create_stripe_payout_request(
        self, data: StripePayoutRequestCreate
    ) -> StripePayoutRequest:
        pass

    @abstractmethod
    async def get_stripe_payout_request_by_payout_id(
        self, payout_id: int
    ) -> Optional[StripePayoutRequest]:
        pass

    @abstractmethod
    async def get_stripe_payout_request_by_stripe_payout_id(
        self, stripe_payout_id: str
    ) -> Optional[StripePayoutRequest]:
        pass

    @abstractmethod
    async def update_stripe_payout_request_by_id(
        self, stripe_payout_request_id: int, data: StripePayoutRequestUpdate
    ) -> Optional[StripePayoutRequest]:
        pass


@final
@tracing.set_repository_name("stripe_payout_request", only_trackable=False)
class StripePayoutRequestRepository(
    PayoutBankDBRepository, StripePayoutRequestRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_stripe_payout_request(
        self, data: StripePayoutRequestCreate
    ) -> StripePayoutRequest:
        stmt = (
            stripe_payout_requests.table.insert()
            .values(
                data.dict(skip_defaults=True), created_at=datetime.now(timezone.utc)
            )
            .returning(*stripe_payout_requests.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return StripePayoutRequest.from_row(row)

    async def get_stripe_payout_request_by_payout_id(
        self, payout_id: int
    ) -> Optional[StripePayoutRequest]:
        stmt = stripe_payout_requests.table.select().where(
            stripe_payout_requests.payout_id == payout_id
        )
        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            # since we have one-to-one mapping to payout
            assert len(rows) == 1
            return StripePayoutRequest.from_row(rows[0])

        return None

    async def get_stripe_payout_request_by_stripe_payout_id(
        self, stripe_payout_id: str
    ) -> Optional[StripePayoutRequest]:
        stmt = stripe_payout_requests.table.select().where(
            stripe_payout_requests.stripe_payout_id == stripe_payout_id
        )
        row = await self._database.replica().fetch_one(stmt)
        return StripePayoutRequest.from_row(row) if row else None

    async def update_stripe_payout_request_by_id(
        self, stripe_payout_request_id: int, data: StripePayoutRequestUpdate
    ) -> Optional[StripePayoutRequest]:
        stmt = (
            stripe_payout_requests.table.update()
            .where(stripe_payout_requests.id == stripe_payout_request_id)
            .values(data.dict_after_json_to_string(skip_defaults=True))
            .returning(*stripe_payout_requests.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return StripePayoutRequest.from_row(row) if row else None
