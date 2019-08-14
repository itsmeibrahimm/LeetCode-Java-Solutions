from typing import List

from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND

from app.payout.service import (
    PaymentAccountRepository,
    PaymentAccountRepositoryInterface,
)
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


router = APIRouter()


@router.post("/", status_code=HTTP_201_CREATED, response_model=PaymentAccount)
async def create_payment_account(
    body: PaymentAccountCreate,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    return await repository.create_payment_account(body)


@router.get(
    "/_get-by-stripe-account-type-account-id",
    status_code=HTTP_200_OK,
    response_model=List[PaymentAccount],
)
async def get_payment_account_by_account_type_account_id(
    stripe_account_type: str,
    stripe_account_id: int,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    payment_accounts = await repository.get_all_payment_accounts_by_account_id_account_type(
        account_id=stripe_account_id, account_type=stripe_account_type
    )
    return payment_accounts


@router.get(
    "/{account_id}",
    response_model=PaymentAccount,
    status_code=HTTP_200_OK,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
)
async def get_payment_account_by_id(
    account_id: int,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    payment_account = await repository.get_payment_account_by_id(account_id)
    if not payment_account:
        raise _payment_account_not_found()
    return payment_account


@router.patch(
    "/{account_id}",
    response_model=PaymentAccount,
    status_code=HTTP_200_OK,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
)
async def update_payment_account_by_id(
    account_id: int,
    body: PaymentAccountUpdate,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    payment_account = await repository.update_payment_account_by_id(
        payment_account_id=account_id, data=body
    )

    if not payment_account:
        raise _payment_account_not_found()

    return payment_account


@router.get(
    "/stripe/{stripe_managed_account_id}",
    response_model=StripeManagedAccount,
    status_code=HTTP_200_OK,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
)
async def get_stripe_managed_account_by_id(
    stripe_managed_account_id: int,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    stripe_managed_account = await repository.get_stripe_managed_account_by_id(
        stripe_managed_account_id=stripe_managed_account_id
    )
    if not stripe_managed_account:
        raise _stripe_managed_account_not_found()

    return stripe_managed_account


@router.post(
    "/stripe/", status_code=HTTP_201_CREATED, response_model=StripeManagedAccount
)
async def create_stripe_managed_account(
    body: StripeManagedAccountCreate,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    return await repository.create_stripe_managed_account(body)


@router.patch(
    "/stripe/{stripe_managed_account_id}",
    response_model=StripeManagedAccount,
    status_code=HTTP_200_OK,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
)
async def update_stripe_managed_account_by_id(
    stripe_managed_account_id: int,
    body: StripeManagedAccountUpdate,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    stripe_managed_account = await repository.update_stripe_managed_account_by_id(
        stripe_managed_account_id=stripe_managed_account_id, data=body
    )

    if not stripe_managed_account:
        raise _stripe_managed_account_not_found()

    return stripe_managed_account


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
