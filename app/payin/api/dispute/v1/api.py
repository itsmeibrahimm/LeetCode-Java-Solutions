from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from structlog.stdlib import BoundLogger

from app.commons.api.models import PaymentException, PaymentErrorResponseBody
from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.payin.core.dispute.model import Dispute, DisputeList
from app.payin.core.dispute.processor import DisputeProcessor
from app.payin.core.exceptions import PayinErrorCode
from app.payin.core.types import DisputePayerIdType, DisputePaymentMethodIdType

api_tags = ["DisputeV1"]
router = APIRouter()


@router.get(
    "/api/v1/disputes/{dispute_id}",
    response_model=Dispute,
    status_code=HTTP_200_OK,
    operation_id="GetDispute",
    responses={
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
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
        Valid values include "dd_stripe_dispute_id", "stripe_dispute_id" (default is "stripe_dispute_id")
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


@router.get(
    "/api/v1/disputes",
    response_model=DisputeList,
    status_code=HTTP_200_OK,
    operation_id="ListDisputes",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def list_disputes(
    payer_id: str = None,
    payer_id_type: DisputePayerIdType = None,
    payment_method_id: str = None,
    payment_method_id_type: DisputePaymentMethodIdType = None,
    log: BoundLogger = Depends(get_logger_from_req),
    dispute_processor: DisputeProcessor = Depends(DisputeProcessor),
) -> DisputeList:
    """
    List disputes.
    - **payer_id**: [string] DoorDash payer_id or stripe_customer_id
    - **payer_id_type**: [string] identify the type of payer_id.
                            Valid values include "payer_id" and "stripe_customer_id"(default is "payer_id")
    - **payment_method_id**: [string] DoorDash payment method id or stripe_payment_method_id.
    - **payment_method_id_type**: [string] identify the type of payment_method_id.
                Valid values include "payment_method_id" and "stripe_payment_method_id"(default is "payment_method_id")
    """
    log.info(
        f"[list_disputes] list_disputes started for payer_id={payer_id} payer_id_type={payer_id_type} payment_method_id={payment_method_id} payment_method_id_type={payment_method_id_type}"
    )
    try:
        disputes = await dispute_processor.list_disputes(
            payer_id=payer_id,
            payer_id_type=payer_id_type,
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )
        log.info("[list_disputes] list_disputes completed")
    except PaymentError as e:
        raise PaymentException(
            http_status_code=(
                HTTP_400_BAD_REQUEST
                if e.error_code
                in (
                    PayinErrorCode.DISPUTE_READ_INVALID_DATA,
                    PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS,
                    PayinErrorCode.DISPUTE_PAYMENT_METHOD_NOT_ASSOCIATED,
                )
                else HTTP_500_INTERNAL_SERVER_ERROR
            ),
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    dispute_list = DisputeList(count=len(disputes), has_more=False, data=disputes)
    return dispute_list
