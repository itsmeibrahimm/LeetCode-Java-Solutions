from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_404_NOT_FOUND,
)

from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.core.errors import PaymentError, JITFundingErrorCode
from app.purchasecard.api.jit_funding.v0.models import (
    JITFunding,
    LinkStoreWithMidRequest,
    LinkStoreWithMidResponse,
    MarqetaJITFundingResponse,
)
from app.purchasecard.api.webhook.v0.models import MarqetaWebhookRequest
from app.purchasecard.container import PurchaseCardContainer
from app.purchasecard.core.jit_funding.models import InternalStoreCardPaymentMetadata
from app.purchasecard.core.jit_funding.processor import CardPaymentMetadataProcessor

api_tags = ["JitFundingV0"]
router = APIRouter()


@router.post(
    "",
    status_code=HTTP_200_OK,
    operation_id="MarqetaJitFunding",
    response_model=MarqetaJITFundingResponse,
    tags=api_tags,
)
def marqeta_webhook(
    request: MarqetaWebhookRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    logger = dependency_container.logger
    logger.info("Rcvd marqeta webhook request", request=request)
    return MarqetaJITFundingResponse(jit_funding=JITFunding())


@router.post(
    "/store_metadata",
    status_code=HTTP_200_OK,
    operation_id="LinkStoreWithMid",
    response_model=LinkStoreWithMidResponse,
    responses={
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
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
        if e.error_code == JITFundingErrorCode.STORE_MASTERCARD_DATA_NOT_FOUND_ERROR:
            status_code = HTTP_404_NOT_FOUND
        else:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status_code,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
