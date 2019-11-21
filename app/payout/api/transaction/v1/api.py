from typing import Optional
from datetime import datetime

import pytz
from fastapi import APIRouter, Depends, Query, Body, Path
from starlette.status import (
    HTTP_200_OK,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_201_CREATED,
)

from app.commons.api.models import PaymentErrorResponseBody
from app.payout.api.transaction.v1 import models
import app.payout.models as payout_models
from app.payout.core.transaction.processor import TransactionProcessors
from app.payout.core.transaction.processors.list_transactions import (
    ListTransactionsRequest,
)
from app.payout.core.transaction.processors.create_transaction import (
    CreateTransactionRequest,
)
from app.payout.core.transaction.processors.reverse_transaction import (
    ReverseTransactionRequest,
)
from app.payout.service import create_transaction_processors

api_tags = ["TransactionsV1"]
router = APIRouter()


@router.get(
    "/",
    status_code=HTTP_200_OK,
    operation_id="ListTransactions",
    response_model=models.TransactionList,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def list_transactions(
    ts_start: Optional[int] = Query(
        default=None, description="Start timestamp epoch seconds (inclusive)"
    ),
    ts_end: Optional[int] = Query(
        default=None, description="End timestamp epoch seconds (inclusive)"
    ),
    target_type: Optional[payout_models.TransactionTargetType] = Query(
        default=None, description="Target type"
    ),
    target_ids: Optional[str] = Query(
        default=None, description="Comma separated target ids"
    ),
    transfer_id: Optional[payout_models.TransferId] = Query(
        default=None, description="Transfer ID"
    ),
    payout_id: Optional[payout_models.PayoutId] = Query(
        default=None, description="Payout ID"
    ),
    payout_account_id: Optional[payout_models.PayoutAccountId] = Query(
        default=None, description="Payment Account ID"
    ),
    unpaid: Optional[bool] = Query(
        default=True, description="Unpaid transaction only if true"
    ),
    transaction_ids: Optional[str] = Query(
        default=None, description="Comma separated transaction ids"
    ),
    transaction_processors: TransactionProcessors = Depends(
        create_transaction_processors
    ),
):
    ##
    # convert the query params from API to biz layer data model
    ##

    # params
    transaction_id_list = None
    if transaction_ids:
        transaction_id_list = list(set(transaction_ids.split(",")))

    target_id_list = None
    if target_ids:
        target_id_list = list(set(target_ids.split(",")))

    start_time = None
    if ts_start:
        start_time = datetime.fromtimestamp(ts_start, tz=pytz.UTC)

    end_time = None
    if ts_end:
        end_time = datetime.fromtimestamp(ts_end, tz=pytz.UTC)

    time_range = payout_models.TimeRange(start_time=start_time, end_time=end_time)

    # construct biz layer data model
    list_transactions_request = ListTransactionsRequest(
        transaction_ids=transaction_id_list,
        target_ids=target_id_list,
        target_type=target_type,
        transfer_id=transfer_id,
        payout_id=payout_id,
        payout_account_id=payout_account_id,
        time_range=time_range,
        unpaid=unpaid,
    )

    ##
    # process the request and format response
    ##
    internal_response = await transaction_processors.list_transactions(
        list_transactions_request
    )
    return models.TransactionList(
        count=internal_response.count, transaction_list=internal_response.data
    )


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    operation_id="CreateTransaction",
    response_model=models.Transaction,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def create_transaction(
    body: models.TransactionCreate = Body(...),
    transaction_processors: TransactionProcessors = Depends(
        create_transaction_processors
    ),
):
    create_transactions_request = CreateTransactionRequest(**body.dict())
    internal_response = await transaction_processors.create_transaction(
        create_transactions_request
    )
    return models.Transaction(**internal_response.dict())


@router.post(
    "/{transaction_id}/reverse",
    status_code=HTTP_200_OK,
    operation_id="ReverseTransaction",
    response_model=models.Transaction,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def reverse_transaction(
    transaction_id: payout_models.TransactionId = Path(
        ..., description="Transaction ID"
    ),
    body: models.ReverseTransaction = Body(...),
    transaction_processors: TransactionProcessors = Depends(
        create_transaction_processors
    ),
):
    reverse_transaction_request = ReverseTransactionRequest(
        transaction_id=transaction_id, reverse_reason=body.reverse_reason
    )
    internal_response = await transaction_processors.reverse_transaction(
        reverse_transaction_request
    )
    return models.Transaction(**internal_response.dict())
