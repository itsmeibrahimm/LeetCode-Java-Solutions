from fastapi import APIRouter, Depends
from app.payout.api.transfer.v1.models import CreateTransfer
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from app.commons.providers.stripe.stripe_models import TransferId
from app.commons.api.models import PaymentErrorResponseBody
from app.payout.api.account.v1 import models
from app.payout.api.transfer.v1.models import (
    SubmitTransfer,
    WeeklyCreateTransfer,
    Transfer,
)
from app.payout.core.transfer.processor import TransferProcessors
from app.payout.core.transfer.processors.create_transfer import CreateTransferRequest
from app.payout.core.transfer.processors.submit_transfer import SubmitTransferRequest
from app.payout.core.transfer.processors.weekly_create_transfer import (
    WeeklyCreateTransferRequest,
)
from app.payout.service import create_transfer_processors


api_tags = ["TransfersV1"]
router = APIRouter()


@router.post(
    "/",
    operation_id="CreateTransfer",
    status_code=HTTP_201_CREATED,
    responses={HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def create_transfer(
    body: CreateTransfer,
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    create_transfer_request = CreateTransferRequest(
        payout_account_id=body.payout_account_id,
        transfer_type=body.transfer_type,
        bank_info_recently_changed=body.bank_info_recently_changed,
        start_time=body.start_time,
        end_time=body.end_time,
        target_id=body.target_id,
        target_type=body.target_type,
        target_business_id=body.target_business_id,
        payout_day=body.payout_day,
        payout_countries=body.payout_countries,
    )
    create_transfer_response = await transfer_processors.create_transfer(
        create_transfer_request
    )
    return Transfer(**create_transfer_response.dict())


@router.post(
    "/{transfer_id}/submit",
    operation_id="SubmitTransfer",
    status_code=HTTP_200_OK,
    responses={HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def submit_transfer(
    transfer_id: TransferId,
    body: SubmitTransfer,
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    submit_transfer_request = SubmitTransferRequest(
        transfer_id=transfer_id,
        retry=body.retry,
        submitted_by=body.submitted_by,
        statement_descriptor=body.statement_descriptor,
        target_type=body.target_type,
        target_id=body.target_id,
        method=body.method,
    )
    submit_transfer_response = await transfer_processors.submit_transfer(
        submit_transfer_request
    )
    return models.Payout(**submit_transfer_response.dict())


# todo: revise url
@router.post(
    "/weekly_create_transfer",
    operation_id="WeeklyCreateTransfer",
    status_code=HTTP_201_CREATED,
    responses={HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def weekly_create_transfer(
    body: WeeklyCreateTransfer,
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    weekly_create_transfer_request = WeeklyCreateTransferRequest(
        payout_day=body.payout_day,
        end_time=body.end_time,
        payout_countries=body.payout_countries,
        unpaid_txn_start_time=body.unpaid_txn_start_time,
        start_time=body.start_time,
        exclude_recently_updated_accounts=body.exclude_recently_updated_accounts,
    )
    weekly_create_transfer_response = await transfer_processors.weekly_create_transfer(
        weekly_create_transfer_request
    )
    return Transfer(**weekly_create_transfer_response.dict())
