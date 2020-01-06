from app.commons.operational_flags import (
    ENABLED_KEY_PREFIX_LIST_FOR_CACHE,
    ENABLED_VERIFICATION_REQUIREMENTS_RETRIEVAL,
    ENABLED_PAYOUT_HANDLE_STRIPE_TRANSFER_EVENT,
)
from app.commons.runtime import runtime


def handle_stripe_transfer_event_enabled() -> bool:
    return runtime.get_bool(ENABLED_PAYOUT_HANDLE_STRIPE_TRANSFER_EVENT, False)


def include_verification_requirements_get_account() -> bool:
    return runtime.get_bool(ENABLED_VERIFICATION_REQUIREMENTS_RETRIEVAL, False)


def enabled_cache_key_prefix_list() -> list:
    return runtime.get_json(ENABLED_KEY_PREFIX_LIST_FOR_CACHE, [])
