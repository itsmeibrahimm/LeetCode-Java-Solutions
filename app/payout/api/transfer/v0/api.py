from typing import Optional

from fastapi import APIRouter
from starlette.requests import Request

from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransferWrite,
    StripeTransfer,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import (
    Transfer,
    TransferWrite,
    TransferUpdate,
)
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


def create_transfer_v0_router(transfer_repo: TransferRepositoryInterface) -> APIRouter:
    router = APIRouter()

    @router.post("/")
    async def create_transfer(data: TransferWrite, request: Request):
        return await transfer_repo.create_transfer(data=data)

    @router.get("/{transfer_id}")
    async def get_transfer_by_id(
        transfer_id: int, request: Request
    ) -> Optional[Transfer]:
        return await transfer_repo.get_transfer_by_id(transfer_id=transfer_id)

    @router.patch("/{transfer_id}")
    async def update_transfer_by_id(
        transfer_id: int, data: TransferUpdate, request: Request
    ) -> Optional[Transfer]:
        return await transfer_repo.update_transfer_by_id(
            transfer_id=transfer_id, data=data
        )

    @router.post("/pgp/stripe/")
    async def create_stripe_transfer(data: StripeTransferWrite, request: Request):
        return await transfer_repo.create_stripe_transfer(data=data)

    @router.get("/pgp/stripe/{stripe_transfer_id}")
    async def get_stripe_transfer_by_id(
        stripe_transfer_id: int, request: Request
    ) -> Optional[StripeTransfer]:
        return await transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer_id
        )

    @router.patch("/pgp/stripe/{stripe_transfer_id}")
    async def update_stripe_transfer_by_id(
        stripe_transfer_id: int, data: StripeTransferUpdate, request: Request
    ) -> Optional[StripeTransfer]:
        return await transfer_repo.update_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer_id, data=data
        )

    return router
