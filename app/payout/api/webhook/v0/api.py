from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from starlette.requests import Request

from app.payout.repository.maindb.transfer import TransferRepositoryInterface
from app.payout.api.webhook.utils.event_handler import (
    STRIPE_WEBHOOK_EVENT_TYPE_HANDLER_MAPPING,
)


def webhook_v0_router(*, transfer_repo: TransferRepositoryInterface) -> APIRouter:
    router = APIRouter()

    @router.post("/{country_code}")
    async def handle_webhook_event(
        country_code: str, event: Dict[str, Any], request: Request
    ):
        # list of event types: https://stripe.com/docs/api/events/types
        event_type = event.get("type", None)
        handler = STRIPE_WEBHOOK_EVENT_TYPE_HANDLER_MAPPING.get(event_type, None)

        if handler:
            rv = await handler(event, country_code, transfer_repo)
            return rv

        raise HTTPException(status_code=400, detail="Error")

    return router
