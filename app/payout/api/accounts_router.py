from typing import Optional

from fastapi import APIRouter
from typing_extensions import Protocol

from app.payout.domain.payout_account.models import PayoutAccount, StripeManagedAccount
from app.payout.domain.payout_account.payment_account_repository import (
    PayoutAccountRepository,
)
from app.payout.domain.payout_account.stripe_managed_account_repository import (
    StripeManagedAccountRepository,
)
from .models import CreatePayoutAccountRequest, CreateStripeManagedAccountRequest


class IAccountRepositories(Protocol):
    payout_accounts: PayoutAccountRepository
    stripe_managed_accounts: StripeManagedAccountRepository


def create_accounts_router(repositories: IAccountRepositories) -> APIRouter:
    router = APIRouter()

    payout_accounts: PayoutAccountRepository = repositories.payout_accounts
    stripe_managed_accounts: StripeManagedAccountRepository = repositories.stripe_managed_accounts

    @router.get("/{id}")
    async def get_account(id: int) -> Optional[PayoutAccount]:
        return await payout_accounts.get_payout_account_by_id(payment_account_id=id)

    @router.post("/")
    async def create_account(request: CreatePayoutAccountRequest) -> PayoutAccount:
        internal_payout_account = PayoutAccount(
            statement_descriptor=request.statement_descriptor,
            account_type=request.account_type,
            entity=request.entity,
        )
        return await payout_accounts.create_payout_account(internal_payout_account)

    @router.get("/sma/{id}")
    async def get_stripe_managed_account(id: int) -> Optional[StripeManagedAccount]:
        return await stripe_managed_accounts.get_stripe_managed_account_by_id(
            stripe_managed_account_id=id
        )

    @router.post("/sma/")
    async def create_stripe_managed_account(
        request: CreateStripeManagedAccountRequest
    ) -> StripeManagedAccount:
        internal_stripe_managed_account = StripeManagedAccount(
            stripe_id=request.stripe_id, country_short_name=request.country_code
        )

        return await stripe_managed_accounts.create_stripe_managed_account(
            internal_stripe_managed_account
        )

    return router
