from app.commons.operational_flags import (
    ENABLED_KEY_PREFIX_LIST_FOR_CACHE,
    ENABLED_VERIFICATION_REQUIREMENTS_RETRIEVAL,
    ENABLED_PAYOUT_HANDLE_STRIPE_TRANSFER_EVENT,
    ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT,
)
from app.commons.runtime import runtime


def handle_stripe_transfer_event_enabled() -> bool:
    return runtime.get_bool(ENABLED_PAYOUT_HANDLE_STRIPE_TRANSFER_EVENT, False)


def include_verification_requirements_get_account() -> bool:
    return runtime.get_bool(ENABLED_VERIFICATION_REQUIREMENTS_RETRIEVAL, False)


def enabled_cache_key_prefix_list() -> list:
    return runtime.get_json(ENABLED_KEY_PREFIX_LIST_FOR_CACHE, [])


def enable_payment_db_lock_for_payout(payout_account_id: int) -> bool:
    return _is_enabled_for_whitelist_or_bucket(
        ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT, payout_account_id
    )


def _is_enabled_for_whitelist_or_bucket(
    feature_flag_file_name: str, account_id: int
) -> bool:
    """
    Check whether the given account is enabled in the whitelist
    """
    data = runtime.get_json(feature_flag_file_name, {})

    # Check if feature flag is turned on for all
    if data.get("enable_all", False):
        return True

    if account_id is None:
        return False

    # Check if account id is in whitelist
    if account_id in data.get("white_list", []):
        return True
    # Check if account id is in enabled bucket
    if account_id % 100 < data.get("bucket", 0):
        return True
    return False
