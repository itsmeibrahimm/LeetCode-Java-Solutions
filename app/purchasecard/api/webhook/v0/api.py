from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK

from app.purchasecard.api.webhook.v0.models import (
    MarqetaWebhookRequest,
    WebhookResponse,
)
from app.purchasecard.container import PurchaseCardContainer

api_tags = ["WebhookV0"]
router = APIRouter()


@router.post(
    "",
    status_code=HTTP_200_OK,
    operation_id="MarqetaWebhook",
    response_model=WebhookResponse,
    tags=api_tags,
)
async def marqeta_webhook(
    request: MarqetaWebhookRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    logger = dependency_container.logger
    logger.debug("Rcvd marqeta webhook request", request=request)
    if not request.transactions:
        return WebhookResponse()

    return await dependency_container.webhook_processor.process_webhook_transactions(
        request.transactions
    )
