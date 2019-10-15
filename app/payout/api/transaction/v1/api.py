from typing import List, Optional

from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR

from app.commons.api.models import PaymentErrorResponseBody
from app.payout.api.transaction.v1 import models
from app.payout import types
from app.payout.core.transaction.processor import TransactionProcessors
from app.payout.core.transaction.processors.list_transactions import (
    ListTransactionsRequest,
    TimeRange,
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
    transaction_ids: Optional[List[types.TransactionId]],
    target_ids: Optional[List[types.PayoutAccountTargetId]],
    target_type: Optional[types.PayoutAccountTargetType],
    transfer_id: Optional[types.TransferId],
    payout_id: Optional[types.PayoutId],
    payout_account_id: Optional[types.PayoutAccountId],
    time_range: Optional[models.TimeRange],
    unpaid: Optional[bool] = True,
    transaction_processors: TransactionProcessors = Depends(
        create_transaction_processors
    ),
):
    list_transactions_request = ListTransactionsRequest(
        transaction_ids=transaction_ids,
        target_ids=target_ids,
        target_type=target_type,
        transfer_id=transfer_id,
        payout_id=payout_id,
        payout_account_id=payout_account_id,
        time_range=TimeRange(**time_range.dict()) if time_range else None,
        unpaid=unpaid,
    )
    internal_response = await transaction_processors.list_transactions(
        list_transactions_request
    )
    return models.TransactionList(
        count=internal_response.count, transaction_list=internal_response.data
    )
