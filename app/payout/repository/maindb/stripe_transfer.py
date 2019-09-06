from datetime import datetime
from abc import ABC, abstractmethod
from typing import Optional
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransfer,
    StripeTransferUpdate,
    StripeTransferCreate,
)


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
    async def update_stripe_transfer_by_id(
        self, stripe_transfer_id: int, data: StripeTransferUpdate
    ) -> Optional[StripeTransfer]:
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
        return StripeTransfer(
            id=345,
            created_at=datetime.utcnow(),
            transfer_id=data.transfer_id,
            stripe_status=data.stripe_status,
        )

    async def get_stripe_transfer_by_id(
        self, stripe_transfer_id: int
    ) -> Optional[StripeTransfer]:
        ...

    async def update_stripe_transfer_by_id(
        self, stripe_transfer_id: int, data: StripeTransferUpdate
    ) -> Optional[StripeTransfer]:
        ...
