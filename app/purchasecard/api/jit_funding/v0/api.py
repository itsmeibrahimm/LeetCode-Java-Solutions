from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK

from app.purchasecard.api.jit_funding.v0.models import (
    JITFunding,
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
