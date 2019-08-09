import os

from app.commons.config.app_config import AppConfig, Secret
from app.commons.database.config import DatabaseConfig


def create_app_config() -> AppConfig:
    """
    Create AppConfig for local environment
    """
    # allow db endpoint (host:port) be overridden in docker compose
    dsj_db_endpoint: str = os.getenv("DSJ_DB_ENDPOINT", "localhost:5435")

    return AppConfig(
        ENVIRONMENT="local",
        DEBUG=True,
        NINOX_ENABLED=False,
        METRICS_CONFIG={"service_name": "payment-service", "cluster": "local"},
        TEST_SECRET=Secret(name="test_secret", value="hello_world_secret"),
        PAYIN_MAINDB_MASTER_URL=Secret(
            name="payin_maindb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYIN_MAINDB_REPLICA_URL=None,
        PAYIN_PAYMENTDB_MASTER_URL=Secret(
            name="payin_paymentdb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        PAYIN_PAYMENTDB_REPLICA_URL=None,
        PAYOUT_MAINDB_MASTER_URL=Secret(
            name="payout_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYOUT_MAINDB_REPLICA_URL=None,
        PAYOUT_BANKDB_MASTER_URL=Secret(
            name="payout_bankdb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/bankdb_dev",
        ),
        PAYOUT_BANKDB_REPLICA_URL=None,
        LEDGER_MAINDB_MASTER_URL=Secret(
            name="ledger_maindb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/maindb_dev",
        ),
        LEDGER_MAINDB_REPLICA_URL=None,
        LEDGER_PAYMENTDB_MASTER_URL=Secret(
            name="ledger_paymentdb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        LEDGER_PAYMENTDB_REPLICA_URL=None,
        DEFAULT_DB_CONFIG=DatabaseConfig(
            replica_pool_size=None, master_pool_size=5, debug=True
        ),
        STRIPE_US_SECRET_KEY=Secret(
            name="stripe_us_secret_key", value="sk_test_NH2ez5KKOx5qPWcNcFhjdr1R"
        ),
        STRIPE_US_PUBLIC_KEY=Secret(
            name="stripe_us_public_key", value="pk_test_NH2ez5KKOx5qPWcNcFhjdr1R"
        ),
        DSJ_API_BASE_URL="",
        DSJ_API_USER_EMAIL=Secret(name="dsj_api_user_email", value=""),
        DSJ_API_USER_PASSWORD=Secret(name="dsj_api_user_password", value=""),
        DSJ_API_JWT_TOKEN_TTL=1800,
    )
