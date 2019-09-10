from datetime import datetime
from abc import ABC, abstractmethod
from typing import Optional, List

from sqlalchemy import and_, not_
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model import stripe_transfers
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransfer,
    StripeTransferUpdate,
    StripeTransferCreate,
)
from app.payout.types import StripePayoutStatus


class StripeTransferRepositoryInterface(ABC):
    @abstractmethod
    async def create_stripe_transfer(
        self, data: StripeTransferCreate
    ) -> StripeTransfer:
        pass

    @abstractmethod
    async def get_stripe_transfer_by_id(
        self, stripe_transfer_id: int
    ) -> Optional[StripeTransfer]:
        pass

    @abstractmethod
    async def get_stripe_transfer_by_stripe_id(
        self, stripe_id: str
    ) -> Optional[StripeTransfer]:
        pass

    @abstractmethod
    async def get_latest_stripe_transfer_by_transfer_id(
        self, transfer_id: int
    ) -> Optional[StripeTransfer]:
        pass

    @abstractmethod
    async def get_stripe_transfers_by_transfer_id(
        self, transfer_id: int
    ) -> List[StripeTransfer]:
        pass

    @abstractmethod
    async def get_all_ongoing_stripe_transfers_by_transfer_id(
        self, transfer_id: int
    ) -> List[StripeTransfer]:
        pass

    @abstractmethod
    async def update_stripe_transfer_by_id(
        self, stripe_transfer_id: int, data: StripeTransferUpdate
    ) -> Optional[StripeTransfer]:
        pass

    @abstractmethod
    async def delete_stripe_transfer_by_stripe_id(self, stripe_id: str) -> int:
        pass


@final
@tracing.track_breadcrumb(repository_name="stripe_transfer")
class StripeTransferRepository(
    PayoutMainDBRepository, StripeTransferRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_stripe_transfer(
        self, data: StripeTransferCreate
    ) -> StripeTransfer:
        # django will insert an empty string if some fields is required but not given as params
        stmt = (
            stripe_transfers.table.insert()
            .values(data.dict(skip_defaults=True), created_at=datetime.utcnow())
            .returning(*stripe_transfers.table.columns.values())
        )

        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return StripeTransfer.from_row(row)

    async def get_stripe_transfer_by_id(
        self, stripe_transfer_id: int
    ) -> Optional[StripeTransfer]:
        stmt = stripe_transfers.table.select().where(
            stripe_transfers.id == stripe_transfer_id
        )
        row = await self._database.replica().fetch_one(stmt)
        return StripeTransfer.from_row(row) if row else None

    async def get_stripe_transfer_by_stripe_id(
        self, stripe_id: str
    ) -> Optional[StripeTransfer]:
        stmt = stripe_transfers.table.select().where(
            stripe_transfers.stripe_id == stripe_id
        )
        row = await self._database.replica().fetch_one(stmt)
        return StripeTransfer.from_row(row) if row else None

    async def get_latest_stripe_transfer_by_transfer_id(
        self, transfer_id: int
    ) -> Optional[StripeTransfer]:
        stmt = (
            stripe_transfers.table.select()
            .where(stripe_transfers.transfer_id == transfer_id)
            .order_by(stripe_transfers.id.desc())
        )
        row = await self._database.replica().fetch_one(stmt)
        return StripeTransfer.from_row(row) if row else None

    async def get_stripe_transfers_by_transfer_id(
        self, transfer_id: int
    ) -> List[StripeTransfer]:
        stmt = stripe_transfers.table.select().where(
            stripe_transfers.transfer_id == transfer_id
        )
        rows = await self._database.replica().fetch_all(stmt)
        return [StripeTransfer.from_row(row) for row in rows]

    async def get_all_ongoing_stripe_transfers_by_transfer_id(
        self, transfer_id: int
    ) -> List[StripeTransfer]:
        stmt = stripe_transfers.table.select().where(
            and_(
                stripe_transfers.transfer_id == transfer_id,
                not_(stripe_transfers.stripe_status == StripePayoutStatus.FAILED.value),
                not_(
                    stripe_transfers.stripe_status == StripePayoutStatus.CANCELED.value
                ),
            )
        )
        rows = await self._database.replica().fetch_all(stmt)
        return [StripeTransfer.from_row(row) for row in rows]

    async def update_stripe_transfer_by_id(
        self, stripe_transfer_id: int, data: StripeTransferUpdate
    ) -> Optional[StripeTransfer]:
        stmt = (
            stripe_transfers.table.update()
            .where(stripe_transfers.id == stripe_transfer_id)
            .values(data.dict(skip_defaults=True))
            .returning(*stripe_transfers.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return StripeTransfer.from_row(row) if row else None

    async def delete_stripe_transfer_by_stripe_id(self, stripe_id: str) -> int:
        stmt = stripe_transfers.table.delete().where(
            stripe_transfers.stripe_id == stripe_id
        )
        multi_result = await self._database.master().execute(stmt)
        return multi_result.matched_row_count
