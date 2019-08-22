from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK

from app.payin.core.webhook.processor import WebhookProcessor

router = APIRouter()


@router.post("/api/v1/webhook/{country_code}", status_code=HTTP_200_OK)
async def handle_payin_webhook(
    country_code: str, webhook_processor: WebhookProcessor = Depends(WebhookProcessor)
):
    webhook_processor.process_webhook(country_code=country_code)
