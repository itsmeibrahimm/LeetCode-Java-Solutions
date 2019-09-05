from uuid import UUID

from fastapi import APIRouter, Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.api.models import PaymentException, PaymentErrorResponseBody
from app.ledger.core.exceptions import (
    MxLedgerProcessError,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
    MxLedgerSubmissionError,
    MxLedgerCreationError,
)
from app.ledger.core.mx_ledger.model import MxLedger

from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_400_BAD_REQUEST,
    HTTP_201_CREATED,
)
from app.ledger.api.mx_ledger.v1.request import CreateMxLedgerRequest

from app.ledger.core.mx_ledger.processor import MxLedgerProcessor

api_tags = ["MxLedgersV1"]
router = APIRouter()


@router.post(
    "/api/v1/mx_ledgers/{mx_ledger_id}/process",
    status_code=HTTP_200_OK,
    response_model=MxLedger,
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
    log: BoundLogger = Depends(get_logger_from_req),
    mx_ledger_processor: MxLedgerProcessor = Depends(MxLedgerProcessor),
):
    """
    Move mx_ledger to PROCESSING.
    """
    log.debug(f"Moving mx_ledger {mx_ledger_id} to PROCESSING.")

    try:
        mx_ledger: MxLedger = await mx_ledger_processor.process(mx_ledger_id)
    except MxLedgerProcessError as e:
        log.error(
            f"[process mx_ledger] [{mx_ledger_id}] Exception caught when processing mx_ledger. {e}"
        )
        raise _mx_ledger_process_internal_error(e)
    except MxLedgerReadError as e:
        log.error(
            f"[process mx_ledger] [{mx_ledger_id}] Cannot find mx_ledger with given id. {e}"
        )
        raise _mx_ledger_not_found(e)
    except MxLedgerInvalidProcessStateError as e:
        log.error(
            f"[process mx_ledger] [{mx_ledger_id}] Cannot process invalid mx_ledger state to PROCESSING {e}"
        )
        raise _mx_ledger_bad_request(e)
    log.info(f"Processed mx_ledger {mx_ledger.id} to PROCESSING.")
    return mx_ledger


@router.post(
    "/api/v1/mx_ledgers/{mx_ledger_id}/submit",
    status_code=HTTP_200_OK,
    response_model=MxLedger,
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
    log: BoundLogger = Depends(get_logger_from_req),
    mx_ledger_processor: MxLedgerProcessor = Depends(MxLedgerProcessor),
):
    """
    Submit mx_ledger.
    """
    log.debug(f"Submitting mx_ledger {mx_ledger_id}.")
    try:
        mx_ledger: MxLedger = await mx_ledger_processor.submit(mx_ledger_id)
    except MxLedgerReadError as e:
        log.error(
            f"[submit mx_ledger] [{mx_ledger_id}] Cannot find mx_ledger with given id. {e}"
        )
        raise _mx_ledger_not_found(e)
    except MxLedgerInvalidProcessStateError as e:
        log.error(
            f"[submit mx_ledger] [{mx_ledger_id}] Cannot submit ledger due to invalid mx_ledger state {e}"
        )
        raise _mx_ledger_bad_request(e)
    except MxLedgerSubmissionError as e:
        log.error(
            f"[submit mx_ledger] [{mx_ledger_id}] Exception caught when processing mx_ledger. {e}"
        )
        raise _mx_ledger_submission_internal_error(e)
    log.info(f"Submitted mx_ledger {mx_ledger_id}.")
    return mx_ledger


def _mx_ledger_process_internal_error(e: MxLedgerProcessError) -> PaymentException:
    return PaymentException(
        http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=e.error_code,
        error_message=e.error_message,
        retryable=e.retryable,
    )


def _mx_ledger_submission_internal_error(
    e: MxLedgerSubmissionError
) -> PaymentException:
    return PaymentException(
        http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=e.error_code,
        error_message=e.error_message,
        retryable=e.retryable,
    )


def _mx_ledger_not_found(e: MxLedgerReadError) -> PaymentException:
    return PaymentException(
        http_status_code=HTTP_404_NOT_FOUND,
        error_code=e.error_code,
        error_message=e.error_message,
        retryable=e.retryable,
    )


def _mx_ledger_bad_request(e: MxLedgerInvalidProcessStateError) -> PaymentException:
    return PaymentException(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_code=e.error_code,
        error_message=e.error_message,
        retryable=e.retryable,
    )


@router.post(
    "/api/v1/mx_ledgers",
    status_code=HTTP_201_CREATED,
    response_model=MxLedger,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    operation_id="CreateMxLedger",
    tags=api_tags,
)
async def create_mx_ledger(
    mx_ledger_request: CreateMxLedgerRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    mx_ledger_processor: MxLedgerProcessor = Depends(MxLedgerProcessor),
):
    """
    Create a mx_ledger
    - **payment_account_id**: str
    - **currency**: str, mx_ledger currency
    - **balance**: int, current balance of mx_ledger
    - **type**: str, mx_ledger type
    """
    log.debug(
        f"Create a mx_ledger for payment_account {mx_ledger_request.payment_account_id}"
    )

    try:
        mx_ledger, mx_transaction = await mx_ledger_processor.create_mx_ledger(
            payment_account_id=mx_ledger_request.payment_account_id,
            currency=mx_ledger_request.currency,
            balance=mx_ledger_request.balance,
            type=mx_ledger_request.type,
        )
        log.info("create mx_ledger completed.")
    except MxLedgerCreationError as e:
        log.error(
            f"[create_mx_ledger] [{mx_ledger_request.payment_account_id}] "
            f"Exception caught when creating mx_ledger and mx_txn. {e}"
        )
        raise _mx_ledger_create_internal_error(e)
    log.info(
        f"Created mx_ledger {mx_ledger.id} for payment_account {mx_ledger.payment_account_id}"
    )
    return mx_ledger


def _mx_ledger_create_internal_error(e: MxLedgerCreationError) -> PaymentException:
    return PaymentException(
        http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=e.error_code,
        error_message=e.error_message,
        retryable=e.retryable,
    )
