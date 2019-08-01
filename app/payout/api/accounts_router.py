from typing import Optional

from fastapi import APIRouter

from app.payout.repository.maindb.payment_account import (
    PaymentAccount,
    PaymentAccountRepository,
)


def create_accounts_router(
    payout_account_repository: PaymentAccountRepository
) -> APIRouter:
    router = APIRouter()

    @router.get("/{id}")
    async def get_account(id: int) -> Optional[PaymentAccount]:
        return await payout_account_repository.get_payment_account_by_id(
            payment_account_id=id
        )

    # TODO bring them back in Payment account v0 API stub
    # @router.post("/")
    # async def create_account(request: CreatePayoutAccountRequest) -> PayoutAccount:
    #     internal_payout_account = PayoutAccount(
    #         statement_descriptor=request.statement_descriptor,
    #         account_type=request.account_type,
    #         entity=request.entity,
    #     )
    #     return await payout_account_repository.create_payout_account(internal_payout_account)

    # @router.get("/sma/{id}")
    # async def get_stripe_managed_account(id: int) -> Optional[StripeManagedAccount]:
    #     return await stripe_managed_accounts.get_stripe_managed_account_by_id(
    #         stripe_managed_account_id=id
    #     )
    #
    # @router.post("/sma/")
    # async def create_stripe_managed_account(
    #     request: CreateStripeManagedAccountRequest
    # ) -> StripeManagedAccount:
    #     internal_stripe_managed_account = StripeManagedAccount(
    #         stripe_id=request.stripe_id, country_short_name=request.country_code
    #     )
    #
    #     return await stripe_managed_accounts.create_stripe_managed_account(
    #         internal_stripe_managed_account
    #     )

    return router
