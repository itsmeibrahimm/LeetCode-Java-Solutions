from fastapi import APIRouter, Body
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from . import models

api_tags = ["AccountsV1"]
router = APIRouter()


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    operation_id="CreatePayoutAccount",
    response_model=models.PayoutAccount,
    tags=api_tags,
)
async def create_payout_account(body: models.CreatePayoutAccount):
    ...


@router.get(
    "/{payout_account_id}",
    status_code=HTTP_200_OK,
    operation_id="GetPayoutAccount",
    response_model=models.PayoutAccount,
    tags=api_tags,
)
async def get_payout_account(payout_account_id: models.PayoutAccountId):
    ...


@router.post(
    "/{payout_account_id}/statement_descriptor",
    operation_id="UpdatePayoutAccountStatementDescriptor",
    status_code=HTTP_200_OK,
    tags=api_tags,
)
async def update_payout_account_statement_descriptor(
    payout_account_id: models.PayoutAccountId
):
    ...


@router.get(
    "/{payout_account_id}/details",
    status_code=HTTP_200_OK,
    operation_id="GetPayoutAccountDetails",
    response_model=models.PayoutAccountDetails,
    tags=api_tags,
)
async def get_payout_account_details(payout_account_id: models.PayoutAccountId):
    ...


@router.post(
    "/{payout_account_id}/verify",
    operation_id="VerifyPayoutAccount",
    status_code=HTTP_200_OK,
    response_model=models.PayoutAccountDetails,
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
    response_model=models.PayoutAccountDetails,
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
    tags=api_tags,
)
async def create_payout_method(
    payout_account_id: models.PayoutAccountId, body: models.CreatePayoutMethod
):
    ...


@router.patch(
    "/{payout_account_id}/payout_methods/{payout_method_id}",
    operation_id="UpdatePayoutMethod",
    status_code=HTTP_200_OK,
    tags=api_tags,
)
async def update_payout_method(
    payout_account_id: models.PayoutAccountId,
    payout_method_id: models.PayoutMethodId,
    body: models.CreatePayoutMethod,
):
    ...


@router.post(
    "/{payout_account_id}/payouts",
    operation_id="CreatePayout",
    response_model=models.Payout,
    tags=api_tags,
)
async def create_payout(
    payout_account_id: models.PayoutAccountId, body: models.PayoutRequest
):
    ...


@router.get(
    "/{payout_account_id}/payouts/{payout_id}",
    operation_id="GetPayout",
    response_model=models.Payout,
    tags=api_tags,
)
async def get_payout(
    payout_account_id: models.PayoutAccountId, payout_id: models.PayoutId
):
    ...
