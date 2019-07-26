from app.commons.config.app_config import AppConfig, Secret

"""
Configurations loaded to Flask App.config dictionary when ENVIRONMENT=local
"""


def create_app_config() -> AppConfig:
    return AppConfig(
        DEBUG=True,
        NINOX_ENABLED=False,
        METRICS_CONFIG={"service_name": "payment-service", "cluster": "local"},
        # Secret configurations start here
        TEST_SECRET=Secret(name="TEST_SECRET", value="local_test_secret"),
        PAYIN_MAINDB_URL=Secret.from_env("PAYIN_MAINDB_URL"),
        PAYOUT_MAINDB_URL=Secret.from_env("PAYOUT_MAINDB_URL"),
        PAYOUT_BANKDB_URL=Secret.from_env("PAYOUT_BANKDB_URL"),
    )
