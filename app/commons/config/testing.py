import os

from .app_config import AppConfig, Secret


def create_app_config() -> AppConfig:
    """
    Create AppConfig for testing environment
    """
    # allow db endpoint (host:port) be overridden in docker compose
    dsj_db_endpoint: str = os.getenv("DSJ_DB_ENDPOINT", "localhost:5435")

    return AppConfig(
        DEBUG=True,
        NINOX_ENABLED=False,
        METRICS_CONFIG={"service_name": "payment-service", "cluster": "testing"},
        # Secret configurations start here
        TEST_SECRET=Secret(name="test_secret", value="hello_world_secret"),
        PAYIN_MAINDB_URL=Secret(
            name="payin_maindb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/maindb_test",
        ),
        PAYOUT_MAINDB_URL=Secret(
            name="payout_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_test",
        ),
        PAYOUT_BANKDB_URL=Secret(
            name="payout_bankdb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/bankdb_test",
        ),
    )
