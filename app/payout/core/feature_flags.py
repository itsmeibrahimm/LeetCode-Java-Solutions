from app.commons.runtime import runtime


def handle_stripe_transfer_event_enabled() -> bool:
    return runtime.get_bool("payout_handle_stripe_transfer_event_enabled.bool", False)


def include_verification_requirements_get_account() -> bool:
    return runtime.get_bool("enable_verification_requirements_retrieval.bool", False)
