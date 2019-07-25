from typing_extensions import Protocol

from app.commons.config.app_config import Secret


class PayoutAppConfig(Protocol):
    DEBUG: bool

    # DB connections
    PAYOUT_MAINDB_URL: Secret
    PAYOUT_BANKDB_URL: Secret
