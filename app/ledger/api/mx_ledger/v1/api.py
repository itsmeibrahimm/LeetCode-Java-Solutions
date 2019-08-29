from uuid import UUID

from fastapi import APIRouter, Depends
from structlog import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.error.errors import PaymentException, PaymentErrorResponseBody
from app.ledger.core.exceptions import (
    MxLedgerProcessError,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
)
from app.ledger.core.mx_ledger.model import MxLedger

from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_400_BAD_REQUEST,
)

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
        log.info("process mx_ledger completed. ")
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


def _mx_ledger_process_internal_error(e: MxLedgerProcessError) -> PaymentException:
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
