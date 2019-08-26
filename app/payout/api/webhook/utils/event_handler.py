from typing import Dict, Any
from datetime import datetime
import json

from app.payout.service import (
    PayoutRepositoryInterface,
    StripePayoutRequestRepositoryInterface,
)
from app.payout.repository.bankdb.model.payout import PayoutUpdate, Payout
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestUpdate,
    StripePayoutRequest,
)
from app.payout.service import PayoutService
from app.commons.providers.dsj_client import DSJClient


STRIPE_RESOURCE_ALLOWED_ACTIONS_TRANSFER = [
    "created",
    "failed",
    "paid",
    "reversed",
    "updated",
]


async def _handle_stripe_transfer_event():
    pass


async def _syncing_events_to_db(
    payout: Payout,
    stripe_payout_request: StripePayoutRequest,
    new_event: Dict[str, Any],
    i_payouts: PayoutRepositoryInterface,
    i_stripe_payout_requests: StripePayoutRequestRepositoryInterface,
    dsj_client: DSJClient,
):
    #
    # Getting the latest events (events may arrive and be processed out of order)
    #

    # NOTE: `stripe_payout_request.events` access pattern does not pass mypy validation
    processed_events = stripe_payout_request.dict().get("events", None)
    if processed_events is None:
        processed_events = []
    processed_events.append(new_event)

    processed_events = list(
        sorted(processed_events, key=lambda evt: evt.get("created", None))
    )
    latest_stripe_event = processed_events[-1]

    event_id = new_event.get("id", None)
    if event_id and latest_stripe_event.get("id", None) == event_id:
        status = new_event.get("data", {}).get("object", {}).get("status", None)
        if status:
            payout_update_data = PayoutUpdate(
                status=status, updated_at=datetime.utcnow()
            )
            await i_payouts.update_payout_by_id(payout.id, payout_update_data)

            stripe_payout_request_update_data = StripePayoutRequestUpdate(
                status=status,
                updated_at=datetime.utcnow(),
                events=json.dumps(processed_events),
            )
            await i_stripe_payout_requests.update_stripe_payout_request_by_id(
                stripe_payout_request.id, stripe_payout_request_update_data
            )

            # TODO: check status mapping
            return await dsj_client.post(
                f"/v1/payouts/{payout.id}/status_update", {"status": status}
            )


async def _handle_stripe_instant_transfer_event(
    event: Dict[str, Any],
    country_code: str,
    i_payouts: PayoutRepositoryInterface,
    i_stripe_payout_requests: StripePayoutRequestRepositoryInterface,
    dsj_client: DSJClient,
) -> Any:
    stripe_payout_id = event.get("data", {}).get("object", {}).get("id", None)
    if stripe_payout_id:
        stripe_payout_request = await i_stripe_payout_requests.get_stripe_payout_request_by_stripe_payout_id(
            stripe_payout_id
        )
        if stripe_payout_request:
            payout = await i_payouts.get_payout_by_id(stripe_payout_request.payout_id)
            if payout:
                await _syncing_events_to_db(
                    payout=payout,
                    stripe_payout_request=stripe_payout_request,
                    new_event=event,
                    i_payouts=i_payouts,
                    i_stripe_payout_requests=i_stripe_payout_requests,
                    dsj_client=dsj_client,
                )


async def handle_stripe_webhook_transfer_event(
    event: Dict[str, Any], country_code: str, payout_service: PayoutService
) -> Any:
    country_code = country_code.lower()

    [resource_type, action] = event.get("type", "").split(".")
    assert resource_type == "transfer"
    assert action in STRIPE_RESOURCE_ALLOWED_ACTIONS_TRANSFER

    stripe_transfer_obj = event.get("data", {}).get("object", None)

    if stripe_transfer_obj:
        tr_type = stripe_transfer_obj.get("method", None)

        if tr_type == "standard":
            await _handle_stripe_transfer_event()
        elif tr_type == "instant":
            await _handle_stripe_instant_transfer_event(
                event=event,
                country_code=country_code,
                i_payouts=payout_service.payouts,
                i_stripe_payout_requests=payout_service.stripe_payout_requests,
                dsj_client=payout_service.dsj_client,
            )
        else:
            # can not handle
            raise ValueError("Not supported transfer type")


STRIPE_WEBHOOK_EVENT_TYPE_HANDLER_MAPPING = {
    "transfer.created": handle_stripe_webhook_transfer_event,
    "transfer.failed": handle_stripe_webhook_transfer_event,
    "transfer.paid": handle_stripe_webhook_transfer_event,
    "transfer.reversed": handle_stripe_webhook_transfer_event,
    "transfer.updated": handle_stripe_webhook_transfer_event,
}
