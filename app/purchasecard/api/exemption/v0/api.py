from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
)

from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.core.errors import PaymentError
from app.purchasecard.api.exemption.v0.models import CreateExemptionRequest

from app.purchasecard.container import PurchaseCardContainer
from app.purchasecard.core.errors import INPUT_PARAM_INVALID_ERROR_CODE
from app.purchasecard.core.exemption.processor import ExemptionProcessor

api_tags = ["ExemptionV0"]
router = APIRouter()


@router.post(
    "",
    status_code=HTTP_201_CREATED,
    operation_id="CreateExemption",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def create_exemption(
    request: CreateExemptionRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    try:
        processor: ExemptionProcessor = dependency_container.exemption_processor
        await processor.create_exemption(
            creator_id=request.creator_id,
            delivery_id=request.delivery_id,
            swipe_amount=request.swipe_amount,
            mid=request.mid,
            dasher_id=request.dasher_id,
            decline_amount=request.declined_amount,
        )
    except PaymentError as e:
        if e.error_code == INPUT_PARAM_INVALID_ERROR_CODE:
            status_code = HTTP_400_BAD_REQUEST
        else:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status_code,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
