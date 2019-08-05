from typing import Optional

from fastapi import APIRouter
from starlette.requests import Request

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
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


def create_account_v0_router(
    *, payment_account_repo: PaymentAccountRepositoryInterface
) -> APIRouter:
    router = APIRouter()

    @router.post("/")
    async def create_payment_account(
        payment_account: PaymentAccountWrite, request: Request
    ):
        return await payment_account_repo.create_payment_account(payment_account)

    @router.get("/{account_id}")
    async def get_payment_account_by_id(
        account_id: int, request: Request
    ) -> Optional[PaymentAccount]:
        return await payment_account_repo.get_payment_account_by_id(account_id)

    @router.patch("/{account_id}")
    async def update_payment_account_by_id(
        account_id: int, payment_account_update: PaymentAccountUpdate, request: Request
    ) -> Optional[PaymentAccount]:
        return await payment_account_repo.update_payment_account_by_id(
            payment_account_id=account_id, data=payment_account_update
        )

    @router.get("/pgp/stripe/{stripe_managed_account_id}")
    async def get_stripe_managed_account(
        stripe_managed_account_id: int, request: Request
    ) -> Optional[StripeManagedAccount]:
        return await payment_account_repo.get_stripe_managed_account_by_id(
            stripe_managed_account_id=stripe_managed_account_id
        )

    @router.post("/pgp/stripe/")
    async def create_stripe_managed_account(
        data: StripeManagedAccountWrite, request: Request
    ) -> StripeManagedAccount:
        return await payment_account_repo.create_stripe_managed_account(data)

    @router.patch("/pgp/stripe/{stripe_managed_account_id}")
    async def update_stripe_managed_account_by_id(
        stripe_managed_account_id: int,
        data: StripeManagedAccountUpdate,
        request: Request,
    ) -> Optional[StripeManagedAccount]:
        return await payment_account_repo.update_stripe_managed_account_by_id(
            stripe_managed_account_id=stripe_managed_account_id, data=data
        )

    return router
