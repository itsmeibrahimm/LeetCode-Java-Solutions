from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from gino import GinoConnection
from typing_extensions import final

from app.commons.database.model import DBRequestModel, DBEntity
from app.payout.repository.maindb.model import payment_accounts
from app.payout.repository.maindb.base import PayoutMainDBRepository


class CreatePaymentAccount(DBRequestModel):
    account_id: int
    account_type: str
    statement_descriptor: str
    entity: str
    resolve_outstanding_balance_frequency: Optional[str] = None
    payout_disabled: Optional[bool] = None
    charges_enabled: Optional[bool] = True
    old_account_id: Optional[int] = None
    upgraded_to_managed_account_at: Optional[datetime] = None
    is_verified_with_stripe: Optional[bool] = None
    transfers_enabled: Optional[bool] = None


# TODO leave as stub here to demonstrate pattern, will revisit when hook up with v0 API model
class PaymentAccount(DBEntity):
    id: int
    account_id: int
    account_type: str
    statement_descriptor: str
    entity: str
    created_at: datetime
    resolve_outstanding_balance_frequency: Optional[str] = None
    payout_disabled: Optional[bool] = None
    charges_enabled: Optional[bool] = True
    old_account_id: Optional[int] = None
    upgraded_to_managed_account_at: Optional[datetime] = None
    is_verified_with_stripe: Optional[bool] = None
    transfers_enabled: Optional[bool] = None


class PaymentAccountRepositoryInterface:
    @abstractmethod
    async def create_payment_account(
        self, request: CreatePaymentAccount
    ) -> PaymentAccount:
        ...

    @abstractmethod
    async def get_payment_account_by_id(
        self, payment_account_id: int
    ) -> Optional[PaymentAccount]:
        ...


@final
@dataclass
class PaymentAccountRepository(
    PaymentAccountRepositoryInterface, PayoutMainDBRepository
):
    async def create_payment_account(
        self, request: CreatePaymentAccount
    ) -> PaymentAccount:
        async with self.database.master().acquire() as connection:  # type: GinoConnection
            stmt = (
                payment_accounts.table.insert()
                .values(request.dict())
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
