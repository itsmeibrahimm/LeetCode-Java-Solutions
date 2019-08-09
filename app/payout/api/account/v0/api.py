from typing import List

from fastapi import APIRouter
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND

from app.commons.error.errors import PaymentErrorResponseBody, PaymentException
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccount,
    PaymentAccountCreate,
    PaymentAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
    StripeManagedAccountCreate,
    StripeManagedAccountUpdate,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


def create_account_v0_router(
    *, payment_account_repo: PaymentAccountRepositoryInterface
) -> APIRouter:
    router = APIRouter()

    @router.post("/", status_code=HTTP_201_CREATED, response_model=PaymentAccount)
    async def create_payment_account(body: PaymentAccountCreate, request: Request):
        return await payment_account_repo.create_payment_account(body)

    @router.get(
        "/_get-by-stripe-account-type-account-id",
        status_code=HTTP_200_OK,
        response_model=List[PaymentAccount],
    )
    async def get_payment_account_by_account_type_account_id(
        stripe_account_type: str, stripe_account_id: int
    ):
        payment_accounts = await payment_account_repo.get_all_payment_accounts_by_account_id_account_type(
            account_id=stripe_account_id, account_type=stripe_account_type
        )
        return payment_accounts

    @router.get(
        "/{account_id}",
        responses={
            HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
            HTTP_200_OK: {"model": PaymentAccount},
        },
    )
    async def get_payment_account_by_id(account_id: int, request: Request):
        payment_account = await payment_account_repo.get_payment_account_by_id(
            account_id
        )
        if not payment_account:
            raise _payment_account_not_found()
        return payment_account

    @router.patch(
        "/{account_id}",
        responses={
            HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
            HTTP_200_OK: {"model": PaymentAccount},
        },
    )
    async def update_payment_account_by_id(
        account_id: int, body: PaymentAccountUpdate, request: Request
    ):
        payment_account = await payment_account_repo.update_payment_account_by_id(
            payment_account_id=account_id, data=body
        )

        if not payment_account:
            raise _payment_account_not_found()

        return payment_account

    @router.get(
        "/stripe/{stripe_managed_account_id}",
        responses={
            HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
            HTTP_200_OK: {"model": StripeManagedAccount},
        },
    )
    async def get_stripe_managed_account_by_id(
        stripe_managed_account_id: int, request: Request
    ):
        stripe_managed_account = await payment_account_repo.get_stripe_managed_account_by_id(
            stripe_managed_account_id=stripe_managed_account_id
        )
        if not stripe_managed_account:
            raise _stripe_managed_account_not_found()

        return stripe_managed_account

    @router.post(
        "/stripe/", status_code=HTTP_201_CREATED, response_model=StripeManagedAccount
    )
    async def create_stripe_managed_account(
        body: StripeManagedAccountCreate, request: Request
    ):
        return await payment_account_repo.create_stripe_managed_account(body)

    @router.patch(
        "/stripe/{stripe_managed_account_id}",
        responses={
            HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
            HTTP_200_OK: {"model": StripeManagedAccount},
        },
    )
    async def update_stripe_managed_account_by_id(
        stripe_managed_account_id: int,
        body: StripeManagedAccountUpdate,
        request: Request,
    ):
        stripe_managed_account = await payment_account_repo.update_stripe_managed_account_by_id(
            stripe_managed_account_id=stripe_managed_account_id, data=body
        )

        if not stripe_managed_account:
            raise _stripe_managed_account_not_found()

        return stripe_managed_account

    return router


def _payment_account_not_found() -> PaymentException:
    return PaymentException(
        http_status_code=HTTP_404_NOT_FOUND,
        error_code="payment_account_not_found",  # not formalize error code yet
        error_message="payment account not found",
        retryable=False,
    )


def _stripe_managed_account_not_found() -> PaymentException:
    return PaymentException(
        http_status_code=HTTP_404_NOT_FOUND,
        error_code="stripe_managed_account_not_found",  # not formalize error code yet
        error_message="stripe managed account not found",
        retryable=False,
    )
