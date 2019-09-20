from typing import Dict, Any
from datetime import datetime
import json
from structlog.stdlib import BoundLogger

from app.payout.service import (
    PayoutRepositoryInterface,
    StripePayoutRequestRepositoryInterface,
    TransferRepositoryInterface,
    StripeTransferRepositoryInterface,
)
from app.payout.repository.bankdb.model.payout import PayoutUpdate, Payout
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestUpdate,
    StripePayoutRequest,
)
from app.payout.repository.maindb.model.stripe_transfer import StripeTransferUpdate
from app.payout.repository.maindb.model.transfer import TransferStatus, TransferUpdate
from app.payout.service import PayoutService
from app.commons.providers.dsj_client import DSJClient
from app.payout.core import feature_flags
from app.commons.context.logger import get_logger

root_logger = get_logger("payout_webhook_handler")

STRIPE_RESOURCE_ALLOWED_ACTIONS_TRANSFER = [
    "created",
    "failed",
    "paid",
    "reversed",
    "updated",
]


async def _handle_stripe_transfer_event(
    event: Dict[str, Any],
    country_code: str,
    i_transfers: TransferRepositoryInterface,
    i_stripe_transfers: StripeTransferRepositoryInterface,
    dsj_client: DSJClient,
    log: BoundLogger = root_logger,
):
    if not feature_flags.handle_stripe_transfer_event_enabled():
        log.info("handle_stripe_transfer_event_enabled is off, skipping...")
        return

    stripe_id = event.get("data", {}).get("object", {}).get("id", None)
    if not stripe_id:
        log.info("not valid stripe_id, skipping...")
        return

    stripe_transfer = await i_stripe_transfers.get_stripe_transfer_by_stripe_id(
        stripe_id=stripe_id
    )
    if not stripe_transfer:
        log.info("stripe transfer not found, skipping...")
        return

    #
    # update stripe_transfer
    #
    stripe_status = event.get("data", {}).get("object", {}).get("status", None)
    stripe_failure_code = (
        event.get("data", {}).get("object", {}).get("failure_code", None)
    )

    if stripe_status is None:
        log.info("stripe status is none, skipping...")
        return

    # TODO: events may arrive out of order, need to prevent timeline mess up
    # Possible Solutions:
    #   1) update stripe_transfers table to have a last_status_update_time
    #   2) fetch from stripe using stripe_id to get the latest status
    # 1) is preferred since 2) will introduce much overhead and redundant traffic

    # this is existing DSJ behavior, carry it over here until above is done
    # logic behind this seems to be `failed` is the definite terminate state
    if stripe_transfer.stripe_status == "failed":
        # don't overwrite a failed status with anything
        log.info("stripe transfer was failed (a terminated state), skipping...")
        return

    stripe_transfer_update_data = StripeTransferUpdate(
        stripe_status=stripe_status, stripe_failure_code=stripe_failure_code
    )
    updated_stripe_transfer = await i_stripe_transfers.update_stripe_transfer_by_id(
        stripe_transfer.id, stripe_transfer_update_data
    )

    assert updated_stripe_transfer
    assert updated_stripe_transfer.id == stripe_transfer.id

    transfer = await i_transfers.get_transfer_by_id(
        transfer_id=stripe_transfer.transfer_id
    )
    if not transfer:
        log.info("transfer not found, skipping...")
        return

    #
    # update transfer
    #
    new_transfer_status = TransferStatus.stripe_status_to_transfer_status(stripe_status)
    transfer_update_data = TransferUpdate(status=new_transfer_status)
    updated_transfer = await i_transfers.update_transfer_by_id(
        transfer.id, transfer_update_data
    )
    assert updated_transfer
    assert updated_transfer.id == transfer.id

    return await dsj_client.post(
        f"/v1/transfers/{transfer.id}/status_update/",
        {"status": stripe_status, "stripe_id": stripe_id},
    )


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
                f"/v1/payouts/{payout.id}/status_update/", {"status": status}
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
            await _handle_stripe_transfer_event(
                event=event,
                country_code=country_code,
                i_transfers=payout_service.transfers,
                i_stripe_transfers=payout_service.stripe_transfers,
                dsj_client=payout_service.dsj_client,
            )
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
