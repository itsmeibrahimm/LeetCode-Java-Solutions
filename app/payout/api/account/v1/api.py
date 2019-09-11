from fastapi import APIRouter, Body, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from structlog.stdlib import BoundLogger

from app.commons.api.models import PaymentErrorResponseBody
from app.commons.context.req_context import get_logger_from_req
from app.payout.core.account.processor import PayoutAccountProcessors
from app.payout.core.account.processors.create_account import CreatePayoutAccountRequest
from app.payout.core.account.processors.create_instant_payout import (
    CreateInstantPayoutRequest,
)
from app.payout.core.account.processors.create_standard_payout import (
    CreateStandardPayoutRequest,
)
from app.payout.core.account.utils import to_external_payout_account
from app.payout.core.account.processors.get_account import GetPayoutAccountRequest
from app.payout.service import create_payout_account_processors
from app.payout.types import PayoutAccountStatementDescriptor, PayoutType
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
    log: BoundLogger = Depends(get_logger_from_req),
):

    log.debug(f"Creating payment_account for {body}.")
    internal_request = CreatePayoutAccountRequest(**body.dict())
    internal_response = await payout_account_processors.create_payout_account(
        internal_request
    )
    external_response = to_external_payout_account(internal_response)
    return models.PayoutAccount(**external_response.dict())


@router.get(
    "/{payout_account_id}",
    status_code=HTTP_200_OK,
    operation_id="GetPayoutAccount",
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def get_payout_account(
    payout_account_id: models.PayoutAccountId,
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_request = GetPayoutAccountRequest(payout_account_id=payout_account_id)
    internal_response = await payout_account_processors.get_payout_account(
        internal_request
    )
    return models.PayoutAccount(**internal_response.payment_account.dict())


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
    payout_account_id: models.PayoutAccountId,
    body: models.PayoutRequest,
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    # The if-else check here is ok for now, since PayoutType only has "standard" and "instant"
    if body.payout_type == PayoutType.STANDARD:
        standard_payout_request = CreateStandardPayoutRequest(
            payout_account_id=payout_account_id,
            amount=body.amount,
            payout_type=body.payout_type,
            target_id=body.target_id,
            target_type=body.target_type,
            transfer_id=body.transfer_id,
            method=body.method,
            submitted_by=body.submitted_by,
        )
        standard_payout_response = await payout_account_processors.create_standard_payout(
            standard_payout_request
        )
        return models.Payout(**standard_payout_response.dict())
    else:
        instant_payout_request = CreateInstantPayoutRequest(
            payout_account_id=payout_account_id,
            amount=body.amount,
            payout_type=body.payout_type,
            payout_id=body.payout_id,
            method=body.method,
            submitted_by=body.submitted_by,
        )
        instant_payout_response = await payout_account_processors.create_instant_payout(
            instant_payout_request
        )
        return models.Payout(**instant_payout_response.dict())
