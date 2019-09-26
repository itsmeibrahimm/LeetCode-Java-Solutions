from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, asc
from typing_extensions import final

from app.commons import tracing
from app.commons.database.client.interface import DBConnection
from app.commons.database.infra import DB
from app.payout.repository.maindb.base import PayoutMainDBRepository
from app.payout.repository.maindb.model import payment_accounts, stripe_managed_accounts
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccount,
    PaymentAccountCreate,
    PaymentAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
    StripeManagedAccountCreate,
    StripeManagedAccountUpdate,
    StripeManagedAccountCreateAndPaymentAccountUpdate,
)
from app.payout.types import AccountType


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
    async def get_last_stripe_managed_account_and_count_by_stripe_id(
        self, stripe_id: str
    ) -> Tuple[Optional[StripeManagedAccount], int]:
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

    @abstractmethod
    async def create_stripe_managed_account_and_update_payment_account(
        self, data: StripeManagedAccountCreateAndPaymentAccountUpdate
    ) -> Tuple[StripeManagedAccount, PaymentAccount]:
        pass


@final
@tracing.track_breadcrumb(repository_name="payment_account")
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
            .values(
                data.dict(skip_defaults=True), created_at=datetime.now(timezone.utc)
            )
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
        row = await self._database.replica().fetch_one(stmt)
        return PaymentAccount.from_row(row) if row else None

    async def get_all_payment_accounts_by_account_id_account_type(
        self, *, account_id: int, account_type: str
    ) -> List[PaymentAccount]:
        stmt = (
            payment_accounts.table.select()
            .order_by(
                asc(payment_accounts.id)
            )  # set order_by pk desc as default for now
            .where(
                and_(
                    payment_accounts.account_id == account_id,
                    payment_accounts.account_type == account_type,
                )
            )
        )

        rows = await self._database.replica().fetch_all(stmt)
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

        row = await self._database.replica().fetch_one(stmt)
        return StripeManagedAccount.from_row(row) if row else None

    async def get_last_stripe_managed_account_and_count_by_stripe_id(
        self, stripe_id: str
    ) -> Tuple[Optional[StripeManagedAccount], int]:
        stmt = (
            stripe_managed_accounts.table.select()
            .where(stripe_managed_accounts.stripe_id == stripe_id)
            .order_by(desc(stripe_managed_accounts.id))
        )
        rows = await self._database.replica().execute(stmt)
        last_row = await self._database.replica().fetch_one(stmt)

        return (
            StripeManagedAccount.from_row(last_row) if last_row else None,
            rows.matched_row_count,
        )

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

    async def create_stripe_managed_account_and_update_payment_account(
        self, data: StripeManagedAccountCreateAndPaymentAccountUpdate
    ) -> Tuple[StripeManagedAccount, PaymentAccount]:
        async with self._database.master().connection() as connection:
            try:
                return await self.execute_create_stripe_managed_account_and_update_payment_account(
                    data=data, db_connection=connection
                )
            except Exception as e:
                raise e

    async def execute_create_stripe_managed_account_and_update_payment_account(
        self,
        data: StripeManagedAccountCreateAndPaymentAccountUpdate,
        db_connection: DBConnection,
    ) -> Tuple[StripeManagedAccount, PaymentAccount]:
        async with db_connection.transaction():
            stripe_managed_account_create = StripeManagedAccountCreate(
                country_shortname=data.country_shortname, stripe_id=data.stripe_id
            )
            stmt = (
                stripe_managed_accounts.table.insert()
                .values(stripe_managed_account_create.dict(skip_defaults=True))
                .returning(*stripe_managed_accounts.table.columns.values())
            )
            row = await db_connection.fetch_one(stmt)
            assert row is not None
            stripe_managed_account = StripeManagedAccount.from_row(row)

            payment_account_update = PaymentAccountUpdate(
                account_id=stripe_managed_account.id,
                account_type=AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
            )
            stmt = (
                payment_accounts.table.update()
                .where(payment_accounts.id == data.payment_account_id)
                .values(payment_account_update.dict(skip_defaults=True))
                .returning(*payment_accounts.table.columns.values())
            )

            row = await db_connection.fetch_one(stmt)
            assert row is not None
            payment_account = PaymentAccount.from_row(row)
            return stripe_managed_account, payment_account
