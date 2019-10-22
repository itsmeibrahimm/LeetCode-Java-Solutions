from typing import cast

from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK

from app.payin.api.webhook.v1.request import StripeWebHookEventRequest
from app.payin.core.webhook.model import StripeWebHookEvent
from app.payin.core.webhook.processor import WebhookProcessor


api_tags = ["PayinWebhookV1"]
router = APIRouter()


@router.post(
    "/webhook/{country_code}",
    status_code=HTTP_200_OK,
    operation_id="HandlePayinWebhook",
    tags=api_tags,
)
async def handle_payin_webhook(
    event: StripeWebHookEventRequest,
    country_code: str,
    webhook_processor: WebhookProcessor = Depends(WebhookProcessor),
):

    await webhook_processor.process_webhook(
        country_code=country_code, stripe_webhook_event=cast(StripeWebHookEvent, event)
    )
