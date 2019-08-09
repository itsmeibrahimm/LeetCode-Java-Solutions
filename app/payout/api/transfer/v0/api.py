from typing import List, Optional

from fastapi import APIRouter
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND

from app.commons.error.errors import PaymentErrorResponseBody, PaymentException
from app.payout.api.response import Acknowledgement
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
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


def create_transfer_v0_router(transfer_repo: TransferRepositoryInterface) -> APIRouter:
    router = APIRouter()

    @router.post("/", status_code=HTTP_201_CREATED, response_model=Transfer)
    async def create_transfer(data: TransferCreate, request: Request):
        return await transfer_repo.create_transfer(data=data)

    @router.get(
        "/{transfer_id}",
        responses={
            HTTP_200_OK: {"model": Transfer},
            HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        },
    )
    async def get_transfer_by_id(transfer_id: int, request: Request):
        transfer = await transfer_repo.get_transfer_by_id(transfer_id=transfer_id)
        if not transfer:
            raise _transfer_not_found()

        return transfer

    @router.patch(
        "/{transfer_id}",
        responses={
            HTTP_200_OK: {"model": Transfer},
            HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        },
    )
    async def update_transfer_by_id(
        transfer_id: int, data: TransferUpdate, request: Request
    ):
        updated_transfer = await transfer_repo.update_transfer_by_id(
            transfer_id=transfer_id, data=data
        )

        if not updated_transfer:
            raise _transfer_not_found()

        return updated_transfer

    @router.post(
        "/stripe/", status_code=HTTP_201_CREATED, response_model=StripeTransfer
    )
    async def create_stripe_transfer(data: StripeTransferCreate, request: Request):
        return await transfer_repo.create_stripe_transfer(data=data)

    @router.get(
        "/stripe/_get-by-stripe-id",
        status_code=HTTP_200_OK,
        response_model=Optional[StripeTransfer],
    )
    async def get_stripe_transfer_by_stripe_id(stripe_id: str):
        return await transfer_repo.get_stripe_transfer_by_stripe_id(stripe_id=stripe_id)

    @router.get(
        "/stripe/_get-by-transfer-id",
        status_code=HTTP_200_OK,
        response_model=List[StripeTransfer],
    )
    async def get_stripe_transfer_by_transfer_id(transfer_id: int, request: Request):
        return await transfer_repo.get_stripe_transfers_by_transfer_id(
            transfer_id=transfer_id
        )

    @router.get(
        "/stripe/{stripe_transfer_id}",
        responses={
            HTTP_200_OK: {"model": StripeTransfer},
            HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        },
    )
    async def get_stripe_transfer_by_id(stripe_transfer_id: int, request: Request):
        stripe_transfer = await transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer_id
        )

        if not stripe_transfer:
            raise _stripe_transfer_not_found()

        return stripe_transfer

    @router.patch(
        "/stripe/{stripe_transfer_id}",
        responses={
            HTTP_200_OK: {"model": StripeTransfer},
            HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        },
    )
    async def update_stripe_transfer_by_id(
        stripe_transfer_id: int, body: StripeTransferUpdate, request: Request
    ) -> Optional[StripeTransfer]:
        updated_stripe_transfer = await transfer_repo.update_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer_id, data=body
        )

        if not updated_stripe_transfer:
            raise _stripe_transfer_not_found()

        return updated_stripe_transfer

    @router.delete(
        "/stripe/_delete-by-stripe-id",
        status_code=HTTP_200_OK,
        response_model=Acknowledgement,
    )
    async def delete_stripe_transfer_by_stripe_id(stripe_id: str):
        await transfer_repo.delete_stripe_transfer_by_stripe_id(stripe_id=stripe_id)
        return Acknowledgement()

    return router


def _transfer_not_found() -> PaymentException:
    return PaymentException(
        http_status_code=HTTP_404_NOT_FOUND,
        error_code="transfer_not_found",  # not formalize error code yet
        error_message="transfer not found",
        retryable=False,
    )


def _stripe_transfer_not_found() -> PaymentException:
    return PaymentException(
        http_status_code=HTTP_404_NOT_FOUND,
        error_code="stripe_transfer_not_found",  # not formalize error code yet
        error_message="stripe transfer not found",
        retryable=False,
    )
