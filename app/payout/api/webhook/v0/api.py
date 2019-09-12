from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from app.payout.api.webhook.utils.event_handler import (
    STRIPE_WEBHOOK_EVENT_TYPE_HANDLER_MAPPING,
)
from app.payout.service import PayoutService, GetPayoutService

router = APIRouter()


@router.post("/{country_code}")
async def handle_webhook_event(
    country_code: str,
    event: Dict[str, Any],
    payout_service: PayoutService = Depends(GetPayoutService),
):
    # list of event types: https://stripe.com/docs/api/events/types
    event_type = event.get("type", None)
    event_id = event.get("id", None)

    payout_service.log.info(
        "processing webhook", event_type=event_type, event_id=event_id
    )

    handler = STRIPE_WEBHOOK_EVENT_TYPE_HANDLER_MAPPING.get(event_type, None)

    if handler:
        rv = await handler(
            event=event, country_code=country_code, payout_service=payout_service
        )
        return rv

    raise HTTPException(status_code=400, detail="Error")
