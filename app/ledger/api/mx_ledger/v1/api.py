from uuid import UUID
from fastapi import APIRouter, Depends
from app.commons.api.models import PaymentErrorResponseBody
from app.ledger.api.mx_ledger.v1 import models

from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_400_BAD_REQUEST,
    HTTP_201_CREATED,
)

from app.ledger.api.mx_ledger.v1.models import MxLedgerRequest
from app.ledger.core.mx_ledger.processor import MxLedgerProcessors
from app.ledger.core.mx_ledger.processors.create_mx_ledger import CreateMxLedgerRequest
from app.ledger.core.mx_ledger.processors.process_mx_ledger import (
    ProcessMxLedgerRequest,
)
from app.ledger.core.mx_ledger.processors.submit_mx_ledger import SubmitMxLedgerRequest
from app.ledger.service import create_mx_ledger_processors

api_tags = ["MxLedgersV1"]
router = APIRouter()


@router.post(
    "/api/v1/mx_ledgers/{mx_ledger_id}/process",
    status_code=HTTP_200_OK,
    responses={
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
    },
    operation_id="ProcessMxLedger",
    tags=api_tags,
)
async def process(
    mx_ledger_id: UUID,
    mx_ledger_processors: MxLedgerProcessors = Depends(create_mx_ledger_processors),
):
    """
    Move mx_ledger to PROCESSING.
    """
    process_mx_ledger_request = ProcessMxLedgerRequest(mx_ledger_id=mx_ledger_id)
    process_mx_ledger_response = await mx_ledger_processors.process_mx_ledger(
        process_mx_ledger_request
    )
    return models.MxLedger(**process_mx_ledger_response.dict())


@router.post(
    "/api/v1/mx_ledgers/{mx_ledger_id}/submit",
    status_code=HTTP_200_OK,
    responses={
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
    },
    operation_id="SubmitMxLedger",
    tags=api_tags,
)
async def submit(
    mx_ledger_id: UUID,
    mx_ledger_processors: MxLedgerProcessors = Depends(create_mx_ledger_processors),
):
    """
    Submit mx_ledger.
    """
    submit_mx_ledger_request = SubmitMxLedgerRequest(mx_ledger_id=mx_ledger_id)
    submit_mx_ledger_response = await mx_ledger_processors.submit_mx_ledger(
        submit_mx_ledger_request
    )
    return models.MxLedger(**submit_mx_ledger_response.dict())


@router.post(
    "/api/v1/mx_ledgers",
    status_code=HTTP_201_CREATED,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    operation_id="CreateMxLedger",
    tags=api_tags,
)
async def create_mx_ledger(
    body: MxLedgerRequest,
    mx_ledger_processors: MxLedgerProcessors = Depends(create_mx_ledger_processors),
):
    """
    Create a mx_ledger
    - **payment_account_id**: str
    - **currency**: str, mx_ledger currency
    - **balance**: int, current balance of mx_ledger
    - **type**: str, mx_ledger type
    """
    create_mx_ledger_request = CreateMxLedgerRequest(
        payment_account_id=body.payment_account_id,
        currency=body.currency,
        balance=body.balance,
        type=body.type,
    )
    create_mx_ledger_response = await mx_ledger_processors.create_mx_ledger(
        create_mx_ledger_request
    )
    return models.MxLedger(**create_mx_ledger_response.dict())
