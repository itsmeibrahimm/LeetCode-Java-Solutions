from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model import managed_account_transfers
from app.payout.repository.maindb.model.managed_account_transfer import (
    ManagedAccountTransferUpdate,
    ManagedAccountTransfer,
    ManagedAccountTransferCreate,
)


class ManagedAccountTransferRepositoryInterface(ABC):
    @abstractmethod
    async def create_managed_account_transfer(
        self, data: ManagedAccountTransferCreate
    ) -> ManagedAccountTransfer:
        pass

    @abstractmethod
    async def get_managed_account_transfer_by_id(
        self, managed_account_transfer_id: int
    ) -> Optional[ManagedAccountTransfer]:
        pass

    @abstractmethod
    async def update_managed_account_transfer_by_id(
        self, managed_account_transfer_id: int, data: ManagedAccountTransferUpdate
    ) -> Optional[ManagedAccountTransfer]:
        pass


@final
@tracing.track_breadcrumb(repository_name="managed_account_transfer")
class ManagedAccountTransferRepository(
    PayoutMainDBRepository, ManagedAccountTransferRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_managed_account_transfer(
        self, data: ManagedAccountTransferCreate
    ) -> ManagedAccountTransfer:
        # django will insert an empty string if some fields is required but not given as params
        stmt = (
            managed_account_transfers.table.insert()
            .values(
                data.dict(skip_defaults=True),
                created_at=datetime.now(timezone.utc),
                stripe_id="",
                stripe_status="",
            )
            .returning(*managed_account_transfers.table.columns.values())
        )

        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return ManagedAccountTransfer.from_row(row)

    async def get_managed_account_transfer_by_id(
        self, managed_account_transfer_id: int
    ) -> Optional[ManagedAccountTransfer]:
        stmt = managed_account_transfers.table.select().where(
            managed_account_transfers.id == managed_account_transfer_id
        )

        row = await self._database.replica().fetch_one(stmt)
        return ManagedAccountTransfer.from_row(row) if row else None

    async def update_managed_account_transfer_by_id(
        self, managed_account_transfer_id: int, data: ManagedAccountTransferUpdate
    ) -> Optional[ManagedAccountTransfer]:
        stmt = (
            managed_account_transfers.table.update()
            .where(managed_account_transfers.id == managed_account_transfer_id)
            .values(data.dict(skip_defaults=True))
            .returning(*managed_account_transfers.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return ManagedAccountTransfer.from_row(row) if row else None
