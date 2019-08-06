from typing import Dict, Any

from app.payout.repository.maindb.transfer import TransferRepositoryInterface


async def handle_stripe_webhook_transfer_event(
    event: Dict[str, Any], country_code: str, transfer_repo: TransferRepositoryInterface
) -> Any:
    # TODO: implement handling logic
    country_code = country_code.lower()
    stripe_transfer_id = event.get("data", {}).get("object", {}).get("id", None)

    # TODO: DB updates... Sending Emails (thru DSJ client)...

    return {
        "id": event.get("id", None),
        "stripe_id": stripe_transfer_id,
        "country_code": country_code,
    }


STRIPE_WEBHOOK_EVENT_TYPE_HANDLER_MAPPING = {
    "transfer.created": handle_stripe_webhook_transfer_event,
    "transfer.failed": handle_stripe_webhook_transfer_event,
    "transfer.paid": handle_stripe_webhook_transfer_event,
    "transfer.reversed": handle_stripe_webhook_transfer_event,
    "transfer.updated": handle_stripe_webhook_transfer_event,
}
