from typing_extensions import Protocol

import attr


@attr.s(frozen=True, auto_attribs=True)
class PayoutAppConfig(Protocol):
    DEBUG: bool

    # DB connections
    PAYOUT_MAINDB_URL: str
    PAYOUT_BANKDB_URL: str
