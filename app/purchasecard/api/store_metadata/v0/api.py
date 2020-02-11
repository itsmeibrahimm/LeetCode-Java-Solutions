from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_400_BAD_REQUEST,
)

from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.core.errors import PaymentError
from app.purchasecard.api.store_metadata.v0.models import (
    LinkStoreWithMidRequest,
    LinkStoreWithMidResponse,
)
from app.purchasecard.container import PurchaseCardContainer
from app.purchasecard.core.errors import INPUT_PARAM_INVALID_ERROR_CODE
from app.purchasecard.core.store_metadata.models import InternalStoreCardPaymentMetadata
from app.purchasecard.core.store_metadata.processor import CardPaymentMetadataProcessor

api_tags = ["StoreMetaDataV0"]
router = APIRouter()


@router.post(
    "",
    status_code=HTTP_200_OK,
    operation_id="LinkStoreWithMid",
    response_model=LinkStoreWithMidResponse,
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def link_store_with_mid(
    request: LinkStoreWithMidRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    try:
        processor: CardPaymentMetadataProcessor = dependency_container.card_payment_metadata_processor
        response: InternalStoreCardPaymentMetadata = await processor.create_or_update_store_card_payment_metadata(
            store_id=request.store_id, mid=request.mid, mname=request.mname
        )
        return LinkStoreWithMidResponse(updated_at=response.updated_at)
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
