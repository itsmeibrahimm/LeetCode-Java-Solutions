from typing import List, Optional

from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND

from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.context.req_context import get_logger_from_req
from app.commons.utils.types import Nullable
from app.payout.api.account.v0.models import (
    PaymentAccount,
    PaymentAccountCreate,
    PaymentAccountUpdate,
    StripeManagedAccount,
    StripeManagedAccountCreate,
    StripeManagedAccountUpdate,
)
from app.payout.repository.maindb.model import payment_account
from app.payout.service import (
    PaymentAccountRepository,
    PaymentAccountRepositoryInterface,
)

api_tags = ["AccountsV0"]
router = APIRouter()


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    response_model=PaymentAccount,
    operation_id="CreatePaymentAccount",
    tags=api_tags,
)
async def create_payment_account(
    body: PaymentAccountCreate,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    internal_request = payment_account.PaymentAccountCreate(
        **{
            k: v.value if issubclass(type(v), Nullable) else v
            for k, v in body.dict(skip_defaults=True).items()
        }
    )
    internal_account = await repository.create_payment_account(internal_request)
    return PaymentAccount(**internal_account.dict())


@router.get(
    "/_get-by-stripe-account-type-account-id",
    status_code=HTTP_200_OK,
    response_model=List[PaymentAccount],
    operation_id="GetPaymentAccountsByAccountTypeAccountId",
    tags=api_tags,
)
async def get_payment_accounts_by_account_type_account_id(
    stripe_account_type: str,
    stripe_account_id: int,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    internal_payment_accounts = await repository.get_all_payment_accounts_by_account_id_account_type(
        account_id=stripe_account_id, account_type=stripe_account_type
    )
    return [
        PaymentAccount(**internal_account.dict())
        for internal_account in internal_payment_accounts
    ]


@router.get(
    "/{account_id}",
    response_model=PaymentAccount,
    status_code=HTTP_200_OK,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
    operation_id="GetPaymentAccountById",
    tags=api_tags,
)
async def get_payment_account_by_id(
    account_id: int,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    internal_account = await repository.get_payment_account_by_id(account_id)
    if not internal_account:
        raise _payment_account_not_found()
    return PaymentAccount(**internal_account.dict())


@router.patch(
    "/{account_id}",
    response_model=PaymentAccount,
    status_code=HTTP_200_OK,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
    operation_id="UpdatePaymentAccountById",
    tags=api_tags,
)
async def update_payment_account_by_id(
    account_id: int,
    body: PaymentAccountUpdate,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    internal_request = payment_account.PaymentAccountUpdate(
        **{
            k: v.value if issubclass(type(v), Nullable) else v
            for k, v in body.dict(skip_defaults=True).items()
        }
    )
    internal_account = await repository.update_payment_account_by_id(
        payment_account_id=account_id, data=internal_request
    )

    if not internal_account:
        raise _payment_account_not_found()

    return PaymentAccount(**internal_account.dict())


@router.get(
    "/stripe/_get-by-stripe-id",
    response_model=Optional[StripeManagedAccount],
    status_code=HTTP_200_OK,
    operation_id="GetStripeManagedAccountByStripeId",
    tags=api_tags,
)
async def get_stripe_managed_account_by_stripe_id(
    stripe_id: str,
    request: Request,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    internal_stripe_managed_account, count = await repository.get_last_stripe_managed_account_and_count_by_stripe_id(
        stripe_id=stripe_id
    )

    if not internal_stripe_managed_account:
        return None

    if count > 1:
        logger = get_logger_from_req(request)
        logger.info(
            "Found multiple StripeManagedAccounts with same stripe id",
            stripe_id=stripe_id,
        )

    return StripeManagedAccount.from_db_model(internal_stripe_managed_account)


@router.get(
    "/stripe/{stripe_managed_account_id}",
    response_model=StripeManagedAccount,
    status_code=HTTP_200_OK,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
    operation_id="GetStripeManagedAccountById",
    tags=api_tags,
)
async def get_stripe_managed_account_by_id(
    stripe_managed_account_id: int,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    internal_stripe_managed_account = await repository.get_stripe_managed_account_by_id(
        stripe_managed_account_id=stripe_managed_account_id
    )
    if not internal_stripe_managed_account:
        raise _stripe_managed_account_not_found()

    return StripeManagedAccount.from_db_model(internal_stripe_managed_account)


@router.post(
    "/stripe/",
    status_code=HTTP_201_CREATED,
    response_model=StripeManagedAccount,
    operation_id="CreateStripeManagedAccount",
    tags=api_tags,
)
async def create_stripe_managed_account(
    body: StripeManagedAccountCreate,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    internal_stripe_managed_account = await repository.create_stripe_managed_account(
        body.to_db_model()
    )
    return StripeManagedAccount.from_db_model(internal_stripe_managed_account)


@router.patch(
    "/stripe/{stripe_managed_account_id}",
    response_model=StripeManagedAccount,
    status_code=HTTP_200_OK,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
    operation_id="UpdateStripeManagedAccountById",
    tags=api_tags,
)
async def update_stripe_managed_account_by_id(
    stripe_managed_account_id: int,
    body: StripeManagedAccountUpdate,
    repository: PaymentAccountRepositoryInterface = Depends(PaymentAccountRepository),
):
    internal_stripe_managed_account = await repository.update_stripe_managed_account_by_id(
        stripe_managed_account_id=stripe_managed_account_id, data=body.to_db_model()
    )

    if not internal_stripe_managed_account:
        raise _stripe_managed_account_not_found()

    return StripeManagedAccount.from_db_model(internal_stripe_managed_account)


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
