from uuid import UUID

from fastapi import APIRouter, Depends
from structlog import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.error.errors import (
    create_payment_error_response_blob,
    PaymentErrorResponseBody,
)
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


def create_mx_ledgers_router() -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/mx_ledgers/{mx_ledger_id}/process", status_code=HTTP_200_OK)
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
            return create_payment_error_response_blob(
                HTTP_500_INTERNAL_SERVER_ERROR,
                PaymentErrorResponseBody(
                    error_code=e.error_code,
                    error_message=e.error_message,
                    retryable=e.retryable,
                ),
            )
        except MxLedgerReadError as e:
            log.error(
                f"[process mx_ledger] [{mx_ledger_id}] Cannot find mx_ledger with given id. {e}"
            )
            return create_payment_error_response_blob(
                HTTP_404_NOT_FOUND,
                PaymentErrorResponseBody(
                    error_code=e.error_code,
                    error_message=e.error_message,
                    retryable=e.retryable,
                ),
            )
        except MxLedgerInvalidProcessStateError as e:
            log.error(
                f"[process mx_ledger] [{mx_ledger_id}] Cannot process invalid mx_ledger state to PROCESSING {e}"
            )
            return create_payment_error_response_blob(
                HTTP_400_BAD_REQUEST,
                PaymentErrorResponseBody(
                    error_code=e.error_code,
                    error_message=e.error_message,
                    retryable=e.retryable,
                ),
            )
        log.info(f"Processed mx_ledger {mx_ledger.id} to PROCESSING.")
        return mx_ledger

    return router
