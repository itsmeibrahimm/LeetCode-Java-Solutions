from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List

from typing_extensions import final

from app.commons.database.infra import DB
from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model import stripe_transfers, transfers
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransferEntity,
    StripeTransferCreate,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import (
    TransferEntity,
    TransferCreate,
    TransferUpdate,
)


class TransferRepositoryInterface(ABC):
    @abstractmethod
    async def create_transfer(self, data: TransferCreate) -> TransferEntity:
        pass

    @abstractmethod
    async def get_transfer_by_id(self, transfer_id: int) -> Optional[TransferEntity]:
        pass

    @abstractmethod
    async def update_transfer_by_id(
        self, transfer_id: int, data: TransferUpdate
    ) -> Optional[TransferEntity]:
        pass

    @abstractmethod
    async def create_stripe_transfer(
        self, data: StripeTransferCreate
    ) -> StripeTransferEntity:
        pass

    @abstractmethod
    async def get_stripe_transfer_by_id(
        self, stripe_transfer_id: int
    ) -> Optional[StripeTransferEntity]:
        pass

    @abstractmethod
    async def get_stripe_transfer_by_stripe_id(
        self, stripe_id: str
    ) -> Optional[StripeTransferEntity]:
        pass

    @abstractmethod
    async def get_stripe_transfers_by_transfer_id(
        self, transfer_id: int
    ) -> List[StripeTransferEntity]:
        pass

    @abstractmethod
    async def update_stripe_transfer_by_id(
        self, stripe_transfer_id: int, data: StripeTransferUpdate
    ) -> Optional[StripeTransferEntity]:
        pass

    @abstractmethod
    async def delete_stripe_transfer_by_stripe_id(self, stripe_id: str) -> bool:
        pass


@final
class TransferRepository(PayoutMainDBRepository, TransferRepositoryInterface):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def get_transfer_by_id(self, transfer_id: int) -> Optional[TransferEntity]:
        stmt = transfers.table.select().where(transfers.id == transfer_id)
        row = await self._database.master().fetch_one(stmt)
        return TransferEntity.from_row(row) if row else None

    async def create_transfer(self, data: TransferCreate) -> TransferEntity:
        stmt = (
            transfers.table.insert()
            .values(data.dict(skip_defaults=True), created_at=datetime.utcnow())
            .returning(*transfers.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return TransferEntity.from_row(row)

    async def update_transfer_by_id(
        self, transfer_id: int, data: TransferUpdate
    ) -> Optional[TransferEntity]:
        stmt = (
            transfers.table.update()
            .where(transfers.id == transfer_id)
            .values(data.dict(skip_defaults=True))
            .returning(*transfers.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return TransferEntity.from_row(row) if row else None

    async def get_stripe_transfer_by_id(
        self, stripe_transfer_id: int
    ) -> Optional[StripeTransferEntity]:
        stmt = stripe_transfers.table.select().where(
            stripe_transfers.id == stripe_transfer_id
        )
        row = await self._database.master().fetch_one(stmt)
        return StripeTransferEntity.from_row(row) if row else None

    async def get_stripe_transfer_by_stripe_id(
        self, stripe_id: str
    ) -> Optional[StripeTransferEntity]:
        stmt = stripe_transfers.table.select().where(
            stripe_transfers.stripe_id == stripe_id
        )
        row = await self._database.master().fetch_one(stmt)
        return StripeTransferEntity.from_row(row) if row else None

    async def create_stripe_transfer(
        self, data: StripeTransferCreate
    ) -> StripeTransferEntity:
        stmt = (
            stripe_transfers.table.insert()
            .values(data.dict(skip_defaults=True), created_at=datetime.utcnow())
            .returning(*stripe_transfers.table.columns.values())
        )

        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return StripeTransferEntity.from_row(row)

    async def update_stripe_transfer_by_id(
        self, stripe_transfer_id: int, data: StripeTransferUpdate
    ) -> Optional[StripeTransferEntity]:
        stmt = (
            stripe_transfers.table.update()
            .where(stripe_transfers.id == stripe_transfer_id)
            .values(data.dict(skip_defaults=True))
            .returning(*stripe_transfers.table.columns.values())
        )

        row = await self._database.master().fetch_one(stmt)
        return StripeTransferEntity.from_row(row) if row else None

    async def get_stripe_transfers_by_transfer_id(
        self, transfer_id: int
    ) -> List[StripeTransferEntity]:
        stmt = stripe_transfers.table.select().where(
            stripe_transfers.transfer_id == transfer_id
        )

        rows = await self._database.master().fetch_all(stmt)
        return [StripeTransferEntity.from_row(row) for row in rows]

    async def delete_stripe_transfer_by_stripe_id(self, stripe_id: str):
        stmt = stripe_transfers.table.delete().where(
            stripe_transfers.stripe_id == stripe_id
        )
        await self._database.master().execute(stmt)
