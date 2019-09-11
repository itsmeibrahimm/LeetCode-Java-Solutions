import os

from app.commons.config.app_config import AppConfig, ApiStatsDConfig, DBConfig
from app.commons.config.secrets import Secret


def create_app_config() -> AppConfig:
    """
    Create AppConfig for testing environment
    """
    # allow db endpoint (host:port) be overridden in docker compose
    dsj_db_endpoint: str = os.getenv("DSJ_DB_ENDPOINT", "localhost:5435")

    return AppConfig(
        ENVIRONMENT="testing",
        DEBUG=True,
        REMOTE_SECRET_ENABLED=False,
        API_STATSD_CONFIG=ApiStatsDConfig(
            TAGS={"service_name": "payment-service", "cluster": "testing"}
        ),
        IDENTITY_SERVICE_HTTP_ENDPOINT="https://identity-service.doorcrawl.com",
        IDENTITY_SERVICE_GRPC_ENDPOINT="identity.doorcrawl-int.com:50051",
        PAYIN_SERVICE_ID=1631011374003906560,
        PAYOUT_SERVICE_ID=1631011374003906560,
        LEDGER_SERVICE_ID=1631011374003906560,
        TEST_SECRET=Secret(name="test_secret", value="hello_world_secret"),
        PAYIN_MAINDB_MASTER_URL=Secret(
            name="payin_maindb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/maindb_test",
        ),
        PAYIN_MAINDB_REPLICA_URL=Secret(
            name="payin_maindb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/maindb_test",
        ),
        PAYIN_PAYMENTDB_MASTER_URL=Secret(
            name="payin_paymentdb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/paymentdb_test",
        ),
        PAYIN_PAYMENTDB_REPLICA_URL=Secret(
            name="payin_paymentdb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/paymentdb_test",
        ),
        PAYOUT_MAINDB_MASTER_URL=Secret(
            name="payout_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_test",
        ),
        PAYOUT_MAINDB_REPLICA_URL=Secret(
            name="payout_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_test",
        ),
        PAYOUT_BANKDB_MASTER_URL=Secret(
            name="payout_bankdb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/bankdb_test",
        ),
        PAYOUT_BANKDB_REPLICA_URL=Secret(
            name="payout_bankdb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/bankdb_test",
        ),
        LEDGER_MAINDB_MASTER_URL=Secret(
            name="ledger_maindb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/maindb_test",
        ),
        LEDGER_MAINDB_REPLICA_URL=Secret(
            name="ledger_maindb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/maindb_test",
        ),
        LEDGER_PAYMENTDB_MASTER_URL=Secret(
            name="ledger_paymentdb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/paymentdb_test",
        ),
        LEDGER_PAYMENTDB_REPLICA_URL=Secret(
            name="ledger_paymentdb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/paymentdb_test",
        ),
        STRIPE_US_SECRET_KEY=Secret(
            name="stripe_us_secret_key", value="sk_test_NH2ez5KKOx5qPWcNcFhjdr1R"
        ),
        STRIPE_US_PUBLIC_KEY=Secret(
            name="stripe_us_public_key", value="pk_test_NH2ez5KKOx5qPWcNcFhjdr1R"
        ),
        DEFAULT_DB_CONFIG=DBConfig(
            replica_pool_max_size=2,
            master_pool_max_size=2,
            debug=False,
            # roll back all database transactions before shutting down
            force_rollback=True,
            closing_timeout_sec=0,  # instantly close unclosed connections
        ),
        AVAILABLE_MAINDB_REPLICAS=["maindb_test"],
        DSJ_API_BASE_URL="https://api.doorcrawl.com",
        DSJ_API_USER_EMAIL=Secret(name="dsj_api_user_email", value=""),
        DSJ_API_USER_PASSWORD=Secret(name="dsj_api_user_password", value=""),
        DSJ_API_JWT_TOKEN_TTL=1800,
    )
