from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT

from app.commons.api.models import PaymentErrorResponseBody
from app.purchasecard.api.jit_funding.v0.models import (
    JITFunding,
    LinkStoreWithMidRequest,
    LinkStoreWithMidResponse,
    MarqetaJITFundingResponse,
)
from app.purchasecard.api.webhook.v0.models import MarqetaWebhookRequest
from app.purchasecard.container import PurchaseCardContainer

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
    status_code=HTTP_201_CREATED,
    operation_id="LinkStoreWithMid",
    response_model=LinkStoreWithMidResponse,
    responses={HTTP_409_CONFLICT: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def link_store_with_mid(
    request: LinkStoreWithMidRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    return LinkStoreWithMidResponse()
