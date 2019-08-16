import os

from app.commons.config.app_config import AppConfig, SentryConfig, DBConfig
from app.commons.config.secrets import Secret


def create_app_config() -> AppConfig:
    """
    Create AppConfig for prod environment
    """
    return AppConfig(
        ENVIRONMENT="prod",
        DEBUG=False,
        REMOTE_SECRET_ENABLED=True,
        METRICS_CONFIG={"service_name": "payment-service", "cluster": "prod"},
        IDENTITY_SERVICE_HTTP_ENDPOINT="https://identity.doordash.com/",
        IDENTITY_SERVICE_GRPC_ENDPOINT="identity.int.doordash.com:50051",
        PAYIN_SERVICE_ID=0,
        PAYOUT_SERVICE_ID=0,
        LEDGER_SERVICE_ID=0,
        TEST_SECRET=Secret(name="hello_world_secret"),
        PAYIN_MAINDB_MASTER_URL=Secret(name="payin_maindb_url"),
        PAYIN_MAINDB_REPLICA_URL=Secret(name="payin_maindb_replica_url"),
        PAYIN_PAYMENTDB_MASTER_URL=Secret(name="payin_paymentdb_url"),
        PAYIN_PAYMENTDB_REPLICA_URL=Secret(name="payin_paymentdb_url"),
        PAYOUT_MAINDB_MASTER_URL=Secret(name="payout_maindb_url"),
        PAYOUT_MAINDB_REPLICA_URL=Secret(name="payout_maindb_replica_url"),
        PAYOUT_BANKDB_MASTER_URL=Secret(name="payout_bankdb_url"),
        PAYOUT_BANKDB_REPLICA_URL=Secret(name="payout_bankdb_replica_url"),
        LEDGER_MAINDB_MASTER_URL=Secret(name="ledger_maindb_url"),
        LEDGER_MAINDB_REPLICA_URL=Secret(name="ledger_maindb_url"),
        LEDGER_PAYMENTDB_MASTER_URL=Secret(name="ledger_paymentdb_url"),
        LEDGER_PAYMENTDB_REPLICA_URL=Secret(name="ledger_paymentdb_url"),
        DEFAULT_DB_CONFIG=DBConfig(
            replica_pool_max_size=2, master_pool_max_size=2, debug=False
        ),
        AVAILABLE_MAINDB_REPLICAS=[
            "doordash_replica1",
            "doordash_replica2",
            "doordash_replica3",
            "doordash_replica4",
        ],
        STRIPE_US_SECRET_KEY=Secret(name="stripe_us_secret_key"),
        STRIPE_US_PUBLIC_KEY=Secret(name="stripe_us_public_key"),
        DSJ_API_BASE_URL="",
        DSJ_API_USER_EMAIL=Secret(name="dsj_api_user_email"),
        DSJ_API_USER_PASSWORD=Secret(name="dsj_api_user_password"),
        DSJ_API_JWT_TOKEN_TTL=1800,
        SENTRY_CONFIG=SentryConfig(
            dsn=Secret(name="sentry_dsn"),
            environment="staging",
            release=f"payment-service@build-{os.getenv('BUILD_NUMBER')}",
        ),
    )
