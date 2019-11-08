import uuid
from typing import Optional


def create_idempotency_key(prefix: Optional[str]) -> str:
    if prefix is not None:
        return prefix + "-" + str(uuid.uuid4())
    else:
        return str(uuid.uuid4())


def _gen_token() -> str:
    return str(uuid.uuid4())


def get_payout_account_lock_name(payout_account_id: int) -> str:
    # Should have a better name
    return "create_transfer_for_payment_account:{}".format(payout_account_id)
