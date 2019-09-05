from fastapi import APIRouter, Body, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.commons.api.models import PaymentErrorResponseBody
from app.payout.core.account.processor import PayoutAccountProcessors
from app.payout.core.account.processors.create_account import CreatePayoutAccountRequest
from app.payout.service import create_payout_account_processors
from app.payout.types import PayoutAccountStatementDescriptor
from . import models

api_tags = ["AccountsV1"]
router = APIRouter()


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    operation_id="CreatePayoutAccount",
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def create_payout_account(
    body: models.CreatePayoutAccount,
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):

    internal_request = CreatePayoutAccountRequest(**body.dict())
    internal_response = await payout_account_processors.create_payout_account(
        internal_request
    )

    return models.PayoutAccount(**internal_response.dict())


@router.get(
    "/{payout_account_id}",
    status_code=HTTP_200_OK,
    operation_id="GetPayoutAccount",
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def get_payout_account(payout_account_id: models.PayoutAccountId):
    ...


@router.patch(
    "/{payout_account_id}/statement_descriptor",
    operation_id="UpdatePayoutAccountStatementDescriptor",
    status_code=HTTP_200_OK,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def update_payout_account_statement_descriptor(
    payout_account_id: models.PayoutAccountId, body: PayoutAccountStatementDescriptor
):
    ...


@router.post(
    "/{payout_account_id}/verify",
    operation_id="VerifyPayoutAccount",
    status_code=HTTP_200_OK,
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def verify_payout_account(
    payout_account_id: models.PayoutAccountId,
    verification_details: models.VerificationDetails,
):
    ...


@router.post(
    "/{payout_account_id}/verify_token",
    operation_id="VerifyPayoutAccountWithToken",
    status_code=HTTP_200_OK,
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def verify_payout_account_with_token(
    payout_account_id: models.PayoutAccountId,
    token: models.PayoutAccountToken = Body(..., embed=True),
):
    ...


@router.post(
    "/{payout_account_id}/payout_methods",
    status_code=HTTP_201_CREATED,
    operation_id="CreatePayoutMethod",
    response_model=models.PayoutMethod,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def create_payout_method(
    payout_account_id: models.PayoutAccountId, body: models.CreatePayoutMethod
):
    ...


@router.post(
    "/{payout_account_id}/payouts",
    operation_id="CreatePayout",
    status_code=HTTP_200_OK,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def create_payout(
    payout_account_id: models.PayoutAccountId, body: models.PayoutRequest
):
    ...
