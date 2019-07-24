import os
from .app_config import AppConfig


def create_app_config() -> AppConfig:
    return AppConfig(
        DEBUG=True,
        NINOX_ENABLED=False,
        # Secret configurations start here
        TEST_SECRET=os.environ.get("TEST_SECRET", "local_test_secret"),
        PAYIN_MAINDB_URL=os.environ.get(
            "PAYIN_MAINDB_URL", "postgresql://payin_user@localhost/maindb_test"
        ),
        PAYOUT_MAINDB_URL=os.environ.get(
            "PAYOUT_MAINDB_URL", "postgresql://payout_user@localhost/maindb_test"
        ),
        PAYOUT_BANKDB_URL=os.environ.get(
            "PAYOUT_BANKDB_URL", "postgresql://payout_user@localhost/bankdb_test"
        ),
    )
