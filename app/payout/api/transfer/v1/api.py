from datetime import datetime
from typing import Optional
import pytz

from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_403_FORBIDDEN,
)

from fastapi import APIRouter, Depends, Body, Path, Query
from app.commons.api.models import PaymentErrorResponseBody
from app.payout.api.transfer.v1 import models as transfer_models
from app.payout.core.exceptions import PayoutErrorCode, PayoutError
from app.payout.core.transfer.processor import TransferProcessors
from app.payout.core.transfer.processors.create_transfer import CreateTransferRequest
from app.payout.core.transfer.processors.get_transfer_by_id import (
    GetTransferByIdRequest,
)
from app.payout.core.transfer.processors.list_transfers import ListTransfersRequest
from app.payout.core.transfer.processors.submit_transfer import SubmitTransferRequest
from app.payout.core.transfer.processors.update_transfer import UpdateTransferRequest
from app.payout.models import TransferId, TimeRange
from app.payout.service import create_transfer_processors


api_tags = ["TransfersV1"]
router = APIRouter()


@router.post(
    "/",
    operation_id="CreateTransfer",
    status_code=HTTP_201_CREATED,
    response_model=transfer_models.Transfer,
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_403_FORBIDDEN: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def create_transfer(
    body: transfer_models.CreateTransfer = Body(...),
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    create_transfer_request = CreateTransferRequest(
        payout_account_id=body.payout_account_id,
        transfer_type=body.transfer_type,
        start_time=body.start_time,
        end_time=body.end_time,
        payout_countries=body.payout_countries,
        payout_day=body.payout_day,
        created_by_id=body.created_by_id,
    )
    create_transfer_response = await transfer_processors.create_transfer(
        create_transfer_request
    )
    if create_transfer_response.error_code == PayoutErrorCode.PAYOUT_COUNTRY_NOT_MATCH:
        raise PayoutError(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayoutErrorCode.PAYOUT_COUNTRY_NOT_MATCH,
            retryable=False,
        )
    elif create_transfer_response.error_code == PayoutErrorCode.PAYMENT_BLOCKED:
        raise PayoutError(
            http_status_code=HTTP_403_FORBIDDEN,
            error_code=PayoutErrorCode.PAYMENT_BLOCKED,
            retryable=False,
        )
    elif (
        create_transfer_response.error_code
        == PayoutErrorCode.NO_UNPAID_TRANSACTION_FOUND
    ):
        raise PayoutError(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayoutErrorCode.NO_UNPAID_TRANSACTION_FOUND,
            retryable=False,
        )
    elif (
        create_transfer_response.error_code
        == PayoutErrorCode.PAYMENT_ACCOUNT_ENTITY_NOT_FOUND
    ):
        raise PayoutError(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayoutErrorCode.PAYMENT_ACCOUNT_ENTITY_NOT_FOUND,
            retryable=False,
        )
    elif create_transfer_response.error_code == PayoutErrorCode.PAYOUT_DAY_NOT_MATCH:
        raise PayoutError(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayoutErrorCode.PAYOUT_DAY_NOT_MATCH,
            retryable=False,
        )
    return transfer_models.Transfer(**create_transfer_response.transfer.dict())


@router.post(
    "/{transfer_id}/submit",
    operation_id="SubmitTransfer",
    status_code=HTTP_200_OK,
    response_model=transfer_models.SubmitTransferResponse,
    responses={HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def submit_transfer(
    transfer_id: TransferId = Path(..., description="Transfer ID"),
    body: transfer_models.SubmitTransfer = Body(...),
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    submit_transfer_request = SubmitTransferRequest(
        transfer_id=transfer_id,
        retry=body.retry,
        submitted_by=body.submitted_by,
        method=body.method,
    )
    submit_transfer_response = await transfer_processors.submit_transfer(
        submit_transfer_request
    )
    return transfer_models.SubmitTransferResponse(**submit_transfer_response.dict())


@router.post(
    "/{transfer_id}",
    operation_id="UpdateTransfer",
    status_code=HTTP_200_OK,
    response_model=transfer_models.Transfer,
    responses={HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def update_transfer(
    transfer_id: TransferId = Path(..., description="Transfer ID"),
    body: transfer_models.UpdateTransfer = Body(...),
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    update_transfer_request = UpdateTransferRequest(
        transfer_id=transfer_id, status=body.status
    )
    update_transfer_response = await transfer_processors.update_transfer(
        update_transfer_request
    )
    return transfer_models.Transfer(**update_transfer_response.transfer.dict())


@router.get(
    "/{transfer_id}",
    operation_id="GetTransferById",
    status_code=HTTP_200_OK,
    response_model=transfer_models.Transfer,
    responses={HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def get_transfer_by_id(
    transfer_id: TransferId = Path(..., description="Transfer ID"),
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    get_transfer_by_id_request = GetTransferByIdRequest(transfer_id=transfer_id)
    get_transfer_by_id_response = await transfer_processors.get_transfer_by_id(
        get_transfer_by_id_request
    )
    return transfer_models.Transfer(**get_transfer_by_id_response.transfer.dict())


@router.get(
    "/",
    operation_id="ListTransfers",
    status_code=HTTP_200_OK,
    response_model=transfer_models.TransferList,
    responses={HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def list_transfers(
    payout_account_ids: Optional[str] = Query(
        default=None, description="Comma separated payout_account ids"
    ),
    status: Optional[str] = Query(default=None, description="Transfer status"),
    ts_start: Optional[int] = Query(
        default=None, description="Start timestamp epoch seconds (inclusive)"
    ),
    ts_end: Optional[int] = Query(
        default=None, description="End timestamp epoch seconds (inclusive)"
    ),
    has_positive_amount: Optional[bool] = Query(
        default=None, description="Boolean flag to filter transfer with positive amount"
    ),
    is_submitted: Optional[bool] = Query(
        default=None, description="Boolean flag to filter transfer with stripe_transfer"
    ),
    offset: Optional[int] = Query(
        default=None, description="Offset of the returned transfers"
    ),
    limit: Optional[int] = Query(
        default=None, description="Limit of the returned transfers"
    ),
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    payout_account_id_list = None
    if payout_account_ids:
        payout_account_id_list = list(set(payout_account_ids.split(",")))

    offset_to_query = 0
    limit_to_query = 50
    if offset:
        offset_to_query = offset
    if limit:
        limit_to_query = limit

    start_time = None
    if ts_start:
        start_time = datetime.fromtimestamp(ts_start, tz=pytz.UTC)

    end_time = None
    if ts_end:
        end_time = datetime.fromtimestamp(ts_end, tz=pytz.UTC)

    time_range = TimeRange(start_time=start_time, end_time=end_time)

    list_transfers_request = ListTransfersRequest(
        payment_account_ids=payout_account_id_list,
        offset=offset_to_query,
        limit=limit_to_query,
        time_range=time_range,
        status=status,
        has_positive_amount=has_positive_amount,
        is_submitted=is_submitted,
    )
    list_transfers_response = await transfer_processors.list_transfers(
        list_transfers_request
    )
    return transfer_models.TransferList(
        transfer_list=list_transfers_response.transfers,
        count=list_transfers_response.count,
    )
