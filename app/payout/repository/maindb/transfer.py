from abc import ABC, abstractmethod
from typing import Optional, List

from gino import GinoConnection
from typing_extensions import final

from app.commons.database.model import Database
from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model import stripe_transfers, transfers
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransfer,
    StripeTransferCreate,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import (
    Transfer,
    TransferCreate,
    TransferUpdate,
)


class TransferRepositoryInterface(ABC):
    @abstractmethod
    async def create_transfer(self, data: TransferCreate) -> Transfer:
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
    async def get_stripe_transfers_by_transfer_id(
        self, transfer_id: int
    ) -> List[StripeTransfer]:
        pass

    @abstractmethod
    async def update_stripe_transfer_by_id(
        self, stripe_transfer_id: int, data: StripeTransferUpdate
    ) -> Optional[StripeTransfer]:
        pass

    @abstractmethod
    async def delete_stripe_transfer_by_stripe_id(self, stripe_id: str) -> bool:
        pass


@final
class TransferRepository(PayoutMainDBRepository, TransferRepositoryInterface):
    def __init__(self, database: Database):
        super().__init__(_database=database)

    async def get_transfer_by_id(self, transfer_id: int) -> Optional[Transfer]:
        stmt = transfers.table.select().where(transfers.id == transfer_id)
        async with self._database.master().acquire() as connection:  # type: GinoConnection

            row = await connection.execution_options(
                timeout=self._database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
        return Transfer.from_orm(row) if row else None

    async def create_transfer(self, data: TransferCreate) -> Transfer:
        stmt = (
            transfers.table.insert()
            .values(data.dict(skip_defaults=True))
            .returning(*transfers.table.columns.values())
        )
        async with self._database.master().acquire() as connection:  # type: GinoConnection

            row = await connection.execution_options(
                timeout=self._database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
        return Transfer.from_orm(row)

    async def update_transfer_by_id(
        self, transfer_id: int, data: TransferUpdate
    ) -> Optional[Transfer]:
        stmt = (
            transfers.table.update()
            .where(transfers.id == transfer_id)
            .values(data.dict(skip_defaults=True))
            .returning(*transfers.table.columns.values())
        )
        async with self._database.master().acquire() as connection:  # type: GinoConnection
            row = await connection.execution_options(
                timeout=self._database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
        return Transfer.from_orm(row) if row else None

    async def get_stripe_transfer_by_id(
        self, stripe_transfer_id: int
    ) -> Optional[StripeTransfer]:
        stmt = stripe_transfers.table.select().where(
            stripe_transfers.id == stripe_transfer_id
        )
        async with self._database.master().acquire() as connection:  # type: GinoConnection
            row = await connection.execution_options(
                timeout=self._database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
        return StripeTransfer.from_orm(row) if row else None

    async def get_stripe_transfer_by_stripe_id(
        self, stripe_id: str
    ) -> Optional[StripeTransfer]:
        stmt = stripe_transfers.table.select().where(
            stripe_transfers.stripe_id == stripe_id
        )

        async with self._database.master().acquire() as connection:  # type: GinoConnection
            row = await connection.execution_options(
                timeout=self._database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
        return StripeTransfer.from_orm(row) if row else None

    async def create_stripe_transfer(
        self, data: StripeTransferCreate
    ) -> StripeTransfer:
        stmt = (
            stripe_transfers.table.insert()
            .values(data.dict(skip_defaults=True))
            .returning(*stripe_transfers.table.columns.values())
        )

        async with self._database.master().acquire() as connection:  # type: GinoConnection

            row = await connection.execution_options(
                timeout=self._database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
        return StripeTransfer.from_orm(row)

    async def update_stripe_transfer_by_id(
        self, stripe_transfer_id: int, data: StripeTransferUpdate
    ) -> Optional[StripeTransfer]:
        stmt = (
            stripe_transfers.table.update()
            .where(stripe_transfers.id == stripe_transfer_id)
            .values(data.dict(skip_defaults=True))
            .returning(*stripe_transfers.table.columns.values())
        )

        async with self._database.master().acquire() as connection:  # type: GinoConnection
            row = await connection.execution_options(
                timeout=self._database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
        return StripeTransfer.from_orm(row) if row else None

    async def get_stripe_transfers_by_transfer_id(
        self, transfer_id: int
    ) -> List[StripeTransfer]:
        stmt = stripe_transfers.table.select().where(
            stripe_transfers.transfer_id == transfer_id
        )

        async with self._database.master().acquire() as connection:  # type: GinoConnection
            rows = await connection.execution_options(
                timeout=self._database.STATEMENT_TIMEOUT_SEC
            ).all(stmt)

        return [StripeTransfer.from_orm(row) for row in rows]

    async def delete_stripe_transfer_by_stripe_id(self, stripe_id: str):
        stmt = stripe_transfers.table.delete().where(
            stripe_transfers.stripe_id == stripe_id
        )

        async with self._database.master().acquire() as connection:  # type: GinoConnection
            await connection.execution_options(
                timeout=self._database.STATEMENT_TIMEOUT_SEC
            ).status(stmt)
