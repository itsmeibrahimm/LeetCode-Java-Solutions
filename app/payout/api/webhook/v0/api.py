from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from app.payout.service import TransferRepository, TransferRepositoryInterface
from app.payout.api.webhook.utils.event_handler import (
    STRIPE_WEBHOOK_EVENT_TYPE_HANDLER_MAPPING,
)


router = APIRouter()


@router.post("/{country_code}")
async def handle_webhook_event(
    country_code: str,
    event: Dict[str, Any],
    transfers: TransferRepositoryInterface = Depends(TransferRepository),
):
    # list of event types: https://stripe.com/docs/api/events/types
    event_type = event.get("type", None)
    handler = STRIPE_WEBHOOK_EVENT_TYPE_HANDLER_MAPPING.get(event_type, None)

    if handler:
        rv = await handler(event, country_code, transfers)
        return rv

    raise HTTPException(status_code=400, detail="Error")
