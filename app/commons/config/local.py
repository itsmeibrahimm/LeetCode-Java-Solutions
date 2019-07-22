import os

from .app_config import AppConfig

"""
Configurations loaded to Flask App.config dictionary when ENVIRONMENT=local
"""
LOCAL = AppConfig(
    DEBUG=True,
    NINOX_ENABLED=False,
    # Secret configurations start here
    TEST_SECRET=os.getenv("TEST_SECRET", "local_test_secret"),
    PAYIN_MAINDB_URL=os.environ["PAYIN_MAINDB_URL"],
    PAYOUT_MAINDB_URL=os.environ["PAYOUT_MAINDB_URL"],
    PAYOUT_BANKDB_URL=os.environ["PAYOUT_BANKDB_URL"],
)
