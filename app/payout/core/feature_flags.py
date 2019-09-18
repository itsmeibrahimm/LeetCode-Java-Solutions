from app.commons.runtime import runtime


def handle_stripe_transfer_event_enabled() -> bool:
    return runtime.get_bool("payout_handle_stripe_transfer_event_enabled.bool", False)
