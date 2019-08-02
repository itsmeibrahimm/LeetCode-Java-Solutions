import logging
from pydantic import BaseModel

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from app.ledger.api.mx_transaction.v1.request import CreateMxTransactionRequest
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.mx_transaction.processor import create_mx_transaction

from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED,
)

from app.ledger.api.mx_transaction.v1.response import HttpResponseBlob

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/api/v1/mx_transactions", status_code=HTTP_201_CREATED)
async def create_mx_transaction_api(reqBody: CreateMxTransactionRequest):
    """
    Create a mx_transaction on DoorDash payments platform

    - **payment_account_id**: DoorDash consumer_id, store_id, or business_id
    - **type**: type that specifies the type of mx_transaction
    - **amount**: mx_transaction amount
    - **currency**: mx_transaction currency
    - **idempotency_key**: mx_transaction idempotency_key.
    - **context**: a context of mx_transaction
    - **metadata**: a metadata of mx_transaction
    """
    logger.info("create_mx_transaction()")

    try:
        mx_transaction: MxTransaction = await create_mx_transaction(
            reqBody.payment_account_id,
            reqBody.type,
            reqBody.amount,
            reqBody.currency,
            reqBody.idempotency_key,
            reqBody.context,
            reqBody.metadata,
        )
        logger.info("create_mx_transaction() completed. ")
    except Exception as e:
        logger.error("create_mx_transaction() exception", e)
        return create_response_blob(
            HTTP_500_INTERNAL_SERVER_ERROR,
            HttpResponseBlob(error_code="code", error_message="error"),
        )

    return mx_transaction


@router.get("/api/v1/mx_transactions/{mx_transaction_id}")
async def get_mx_transaction(mx_transaction_id: str) -> JSONResponse:

    logger.info("get_mx_transaction() mx_transaction_id=%s", mx_transaction_id)

    return create_response_blob(
        HTTP_501_NOT_IMPLEMENTED,
        HttpResponseBlob(error_code="code", error_message="error"),
    )


def create_response_blob(status_code: int, resp_blob: BaseModel):
    return JSONResponse(status_code=status_code, content=jsonable_encoder(resp_blob))
