from abc import ABC, abstractmethod
from datetime import datetime

from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model import stripe_managed_account_transfers
from app.payout.repository.bankdb.model.stripe_managed_account_transfer import (
    StripeManagedAccountTransfer,
    StripeManagedAccountTransferCreate,
)


class StripeManagedAccountTransferRepositoryInterface(ABC):
    @abstractmethod
    async def create_stripe_managed_account_transfer(
        self, data: StripeManagedAccountTransferCreate
    ) -> StripeManagedAccountTransfer:
        pass


@final
@tracing.track_breadcrumb(repository_name="stripe_managed_account_transfer")
class StripeManagedAccountTransferRepository(
    PayoutBankDBRepository, StripeManagedAccountTransferRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_stripe_managed_account_transfer(
        self, data: StripeManagedAccountTransferCreate
    ) -> StripeManagedAccountTransfer:
        now = datetime.utcnow()
        stmt = (
            stripe_managed_account_transfers.table.insert()
            .values(data.dict(skip_defaults=True), created_at=now, updated_at=now)
            .returning(*stripe_managed_account_transfers.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return StripeManagedAccountTransfer.from_row(row)
