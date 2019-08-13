from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Optional

from sqlalchemy import and_
from typing_extensions import final

from app.commons.database.infra import DB
from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model import payment_accounts, stripe_managed_accounts
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccount,
    PaymentAccountUpdate,
    PaymentAccountCreate,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
    StripeManagedAccountUpdate,
    StripeManagedAccountCreate,
)


class PaymentAccountRepositoryInterface(ABC):
    @abstractmethod
    async def create_payment_account(
        self, data: PaymentAccountCreate
    ) -> PaymentAccount:
        pass

    @abstractmethod
    async def get_payment_account_by_id(
        self, payment_account_id: int
    ) -> Optional[PaymentAccount]:
        pass

    @abstractmethod
    async def get_all_payment_accounts_by_account_id_account_type(
        self, *, account_id: int, account_type: str
    ) -> List[PaymentAccount]:
        pass

    @abstractmethod
    async def update_payment_account_by_id(
        self, payment_account_id: int, data: PaymentAccountUpdate
    ) -> Optional[PaymentAccount]:
        pass

    @abstractmethod
    async def get_stripe_managed_account_by_id(
        self, stripe_managed_account_id: int
    ) -> Optional[StripeManagedAccount]:
        pass

    @abstractmethod
    async def create_stripe_managed_account(
        self, data: StripeManagedAccountCreate
    ) -> StripeManagedAccount:
        pass

    @abstractmethod
    async def update_stripe_managed_account_by_id(
        self, stripe_managed_account_id: int, data: StripeManagedAccountUpdate
    ) -> Optional[StripeManagedAccount]:
        pass


@final
class PaymentAccountRepository(
    PayoutMainDBRepository, PaymentAccountRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_payment_account(
        self, data: PaymentAccountCreate
    ) -> PaymentAccount:
        stmt = (
            payment_accounts.table.insert()
            .values(data.dict(skip_defaults=True), created_at=datetime.utcnow())
            .returning(*payment_accounts.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return PaymentAccount.from_row(row)

    async def get_payment_account_by_id(
        self, payment_account_id: int
    ) -> Optional[PaymentAccount]:
        stmt = payment_accounts.table.select().where(
            payment_accounts.id == payment_account_id
        )
        row = await self._database.master().fetch_one(stmt)
        return PaymentAccount.from_row(row) if row else None

    async def get_all_payment_accounts_by_account_id_account_type(
        self, *, account_id: int, account_type: str
    ) -> List[PaymentAccount]:
        stmt = payment_accounts.table.select().where(
            and_(
                payment_accounts.account_id == account_id,
                payment_accounts.account_type == account_type,
            )
        )

        rows = await self._database.master().fetch_all(stmt)
        if rows:
            return [PaymentAccount.from_row(row) for row in rows]
        else:
            return []

    async def update_payment_account_by_id(
        self, payment_account_id: int, data: PaymentAccountUpdate
    ) -> Optional[PaymentAccount]:
        stmt = (
            payment_accounts.table.update()
            .where(payment_accounts.id == payment_account_id)
            .values(data.dict(skip_defaults=True))
            .returning(*payment_accounts.table.columns.values())
        )

        row = await self._database.master().fetch_one(stmt)
        return PaymentAccount.from_row(row) if row else None

    async def get_stripe_managed_account_by_id(
        self, stripe_managed_account_id: int
    ) -> Optional[StripeManagedAccount]:
        stmt = stripe_managed_accounts.table.select().where(
            stripe_managed_accounts.id == stripe_managed_account_id
        )

        row = await self._database.master().fetch_one(stmt)
        return StripeManagedAccount.from_row(row) if row else None

    async def create_stripe_managed_account(
        self, data: StripeManagedAccountCreate
    ) -> StripeManagedAccount:
        stmt = (
            stripe_managed_accounts.table.insert()
            .values(data.dict(skip_defaults=True))
            .returning(*stripe_managed_accounts.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return StripeManagedAccount.from_row(row)

    async def update_stripe_managed_account_by_id(
        self, stripe_managed_account_id: int, data: StripeManagedAccountUpdate
    ) -> Optional[StripeManagedAccount]:
        stmt = (
            stripe_managed_accounts.table.update()
            .where(stripe_managed_accounts.id == stripe_managed_account_id)
            .values(data.dict(skip_defaults=True))
            .returning(*stripe_managed_accounts.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return StripeManagedAccount.from_row(row) if row else None
