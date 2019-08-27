from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from structlog import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.error.errors import PaymentError, PaymentException
from app.payin.core.dispute.model import Dispute
from app.payin.core.dispute.processor import DisputeProcessor
from app.payin.core.exceptions import PayinErrorCode

router = APIRouter()


@router.get("/api/v1/disputes/{dispute_id}", status_code=HTTP_200_OK)
async def get_dispute(
    dispute_id: str,
    dispute_id_type: str = None,
    log: BoundLogger = Depends(get_logger_from_req),
    dispute_processor: DisputeProcessor = Depends(DisputeProcessor),
) -> Dispute:
    """
    Get dispute.
    - **dispute_id**: id for dispute in dispute table
    - **dispute_id_type**: [string] identify the type of id for the dispute.
        Valid values include "stripe_dispute_id", "pgp_dispute_id" (default is "pgp_dispute_id")
    """
    log.info("[get_dispute] get_dispute started for dispute_id=%s", dispute_id)
    try:
        dispute: Dispute = await dispute_processor.get(
            dispute_id=dispute_id, dispute_id_type=dispute_id_type
        )
        log.info("[get_dispute] get_dispute completed for dispute_id=%s", dispute_id)
    except PaymentError as e:
        raise PaymentException(
            http_status_code=(
                HTTP_404_NOT_FOUND
                if e.error_code == PayinErrorCode.DISPUTE_NOT_FOUND
                else HTTP_500_INTERNAL_SERVER_ERROR
            ),
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    return dispute
