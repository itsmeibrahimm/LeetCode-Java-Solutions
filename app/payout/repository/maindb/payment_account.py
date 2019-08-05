from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from gino import GinoConnection
from typing_extensions import Protocol, final

from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model import payment_accounts, stripe_managed_accounts
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccount,
    PaymentAccountWrite,
    PaymentAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
    StripeManagedAccountWrite,
    StripeManagedAccountUpdate,
)


class PaymentAccountRepositoryInterface(Protocol):
    @abstractmethod
    async def create_payment_account(self, data: PaymentAccountWrite) -> PaymentAccount:
        ...

    @abstractmethod
    async def get_payment_account_by_id(
        self, payment_account_id: int
    ) -> Optional[PaymentAccount]:
        ...

    @abstractmethod
    async def update_payment_account_by_id(
        self, payment_account_id: int, data: PaymentAccountUpdate
    ) -> Optional[PaymentAccount]:
        ...

    @abstractmethod
    async def get_stripe_managed_account_by_id(
        self, stripe_managed_account_id: int
    ) -> Optional[StripeManagedAccount]:
        ...

    @abstractmethod
    async def create_stripe_managed_account(
        self, data: StripeManagedAccountWrite
    ) -> StripeManagedAccount:
        ...

    @abstractmethod
    async def update_stripe_managed_account_by_id(
        self, stripe_managed_account_id: int, data: StripeManagedAccountUpdate
    ) -> Optional[StripeManagedAccount]:
        ...


@final
@dataclass
class PaymentAccountRepository(
    PayoutMainDBRepository, PaymentAccountRepositoryInterface
):
    async def create_payment_account(self, data: PaymentAccountWrite) -> PaymentAccount:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = (
                payment_accounts.table.insert()
                .values(data.dict(skip_defaults=True))
                .returning(*payment_accounts.table.columns.values())
            )
            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return PaymentAccount.from_orm(row)

    async def get_payment_account_by_id(
        self, payment_account_id: int
    ) -> Optional[PaymentAccount]:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = payment_accounts.table.select().where(
                payment_accounts.id == payment_account_id
            )
            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return PaymentAccount.from_orm(row) if row else None

    async def update_payment_account_by_id(
        self, payment_account_id: int, data: PaymentAccountUpdate
    ) -> Optional[PaymentAccount]:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = (
                payment_accounts.table.update()
                .where(payment_accounts.id == payment_account_id)
                .values(data.dict(skip_defaults=True))
                .returning(*payment_accounts.table.columns.values())
            )
            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return PaymentAccount.from_orm(row) if row else None

    async def get_stripe_managed_account_by_id(
        self, stripe_managed_account_id: int
    ) -> Optional[StripeManagedAccount]:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = stripe_managed_accounts.table.select().where(
                stripe_managed_accounts.id == stripe_managed_account_id
            )

            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return StripeManagedAccount.from_orm(row) if row else None

    async def create_stripe_managed_account(
        self, data: StripeManagedAccountWrite
    ) -> StripeManagedAccount:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = (
                stripe_managed_accounts.table.insert()
                .values(data.dict(skip_defaults=True))
                .returning(*stripe_managed_accounts.table.columns.values())
            )

            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return StripeManagedAccount.from_orm(row)

    async def update_stripe_managed_account_by_id(
        self, stripe_managed_account_id: int, data: StripeManagedAccountUpdate
    ) -> Optional[StripeManagedAccount]:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = (
                stripe_managed_accounts.table.update()
                .where(stripe_managed_accounts.id == stripe_managed_account_id)
                .values(data.dict(skip_defaults=True))
                .returning(*stripe_managed_accounts.table.columns.values())
            )
            row = await connection.execution_options(
                timeout=self.database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return StripeManagedAccount.from_orm(row) if row else None
