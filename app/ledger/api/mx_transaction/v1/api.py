from fastapi import APIRouter, Depends
from app.commons.api.exceptions import create_payment_error_response_blob
from app.commons.api.models import PaymentErrorResponseBody
from app.ledger.api.mx_transaction.v1 import models
from app.ledger.api.mx_transaction.v1.models import MxTransactionRequest
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED,
    HTTP_200_OK,
)

from app.ledger.core.mx_transaction.processor import MxTransactionProcessors
from app.ledger.core.mx_transaction.processors.create_mx_transaction import (
    CreateMxTransactionRequest,
)
from app.ledger.service import create_mx_transaction_processors

api_tags = ["MxTransactionsV1"]
router = APIRouter()


@router.post(
    "/api/v1/mx_transactions",
    status_code=HTTP_201_CREATED,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    operation_id="CreateMxTransaction",
    tags=api_tags,
)
async def create_mx_transaction(
    body: MxTransactionRequest,
    mx_transaction_processors: MxTransactionProcessors = Depends(
        create_mx_transaction_processors
    ),
):
    """
        Create a mx_transaction on DoorDash payments platform

        - **payment_account_id**: str
        - **target_type**: MxTransactionType, type of mx_transaction
        - **amount**: int, mx_transaction amount
        - **currency**: Currency, mx_transaction currency
        - **idempotency_key**: str, mx_transaction idempotency_key.
        - **routing_key**: datetime, created_at of txn in DSJ or POS confirmation time
        - **interval_type**: MxLedgerIntervalType, specify how long the mx_ledger will be opened
        - **target_id**: Optional[str], id corresponding to mx_transaction type, e.g. delivery_id
        - **context**: Optional[Json], a context of mx_transaction
        - **metadata**: Optional[Json], metadata of mx_transaction
        - **legacy_transaction_id**: Optional[str], points to the corresponding txn in DSJ, used for migration purpose
    """
    create_mx_transaction_request = CreateMxTransactionRequest(
        payment_account_id=body.payment_account_id,
        target_type=body.target_type,
        amount=body.amount,
        currency=body.currency,
        idempotency_key=body.idempotency_key,
        routing_key=body.routing_key,
        interval_type=body.interval_type,
        target_id=body.target_id,
        context=body.context,
        metadata=body.metadata,
        legacy_transaction_id=body.legacy_transaction_id,
    )
    create_mx_transaction_response = await mx_transaction_processors.create_mx_transaction(
        create_mx_transaction_request
    )
    return models.MxTransaction(**create_mx_transaction_response.dict())


@router.post(
    "/api/v1/mx_transactions/{mx_transaction_id}",
    status_code=HTTP_200_OK,
    responses={HTTP_501_NOT_IMPLEMENTED: {"model": PaymentErrorResponseBody}},
    operation_id="GetMxTransaction",
    tags=api_tags,
)
async def get_mx_transaction(mx_transaction_id: str, request: Request) -> JSONResponse:
    return create_payment_error_response_blob(
        HTTP_501_NOT_IMPLEMENTED,
        PaymentErrorResponseBody(
            error_code="not implemented",
            error_message="not implemented",
            retryable=False,
        ),
    )
