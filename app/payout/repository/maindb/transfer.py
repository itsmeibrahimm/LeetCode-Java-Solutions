from abc import abstractmethod
from typing import Optional

from gino import GinoConnection

from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model import transfers, stripe_transfers
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransferUpdate,
    StripeTransfer,
    StripeTransferWrite,
)
from app.payout.repository.maindb.model.transfer import (
    Transfer,
    TransferWrite,
    TransferUpdate,
)


class TransferRepositoryInterface:
    @abstractmethod
    async def create_transfer(self, data: TransferWrite) -> Transfer:
        pass

    @abstractmethod
    async def get_transfer_by_id(self, transfer_id: int) -> Optional[Transfer]:
        pass

    @abstractmethod
    async def update_transfer_by_id(
        self, transfer_id: int, data: TransferUpdate
    ) -> Optional[Transfer]:
        pass

    @abstractmethod
    async def create_stripe_transfer(self, data: StripeTransferWrite) -> StripeTransfer:
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


class TransferRepository(PayoutMainDBRepository, TransferRepositoryInterface):
    async def get_transfer_by_id(self, transfer_id: int) -> Optional[Transfer]:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = transfers.table.select().where(transfers.id == transfer_id)

            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return Transfer.from_orm(row) if row else None

    async def create_transfer(self, data: TransferWrite) -> Transfer:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = (
                transfers.table.insert()
                .values(data.dict(skip_defaults=True))
                .returning(*transfers.table.columns.values())
            )

            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return Transfer.from_orm(row)

    async def update_transfer_by_id(
        self, transfer_id: int, data: TransferUpdate
    ) -> Optional[Transfer]:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = (
                transfers.table.update()
                .where(transfers.id == transfer_id)
                .values(data.dict(skip_defaults=True))
                .returning(*transfers.table.columns.values())
            )
            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return Transfer.from_orm(row) if row else None

    async def get_stripe_transfer_by_id(
        self, stripe_transfer_id: int
    ) -> Optional[StripeTransfer]:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = stripe_transfers.table.select().where(
                stripe_transfers.id == stripe_transfer_id
            )

            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return StripeTransfer.from_orm(row) if row else None

    async def create_stripe_transfer(self, data: StripeTransferWrite) -> StripeTransfer:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = (
                stripe_transfers.table.insert()
                .values(data.dict(skip_defaults=True))
                .returning(*stripe_transfers.table.columns.values())
            )

            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return StripeTransfer.from_orm(row)

    async def update_stripe_transfer_by_id(
        self, stripe_transfer_id: int, data: StripeTransferUpdate
    ) -> Optional[StripeTransfer]:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = (
                stripe_transfers.table.update()
                .where(stripe_transfers.id == stripe_transfer_id)
                .values(data.dict(skip_defaults=True))
                .returning(*stripe_transfers.table.columns.values())
            )
            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return StripeTransfer.from_orm(row) if row else None
