import os

from apscheduler.triggers.cron import CronTrigger

from app.commons.config.app_config import (
    AppConfig,
    ApiStatsDConfig,
    DBConfig,
    SentryConfig,
)
from app.commons.config.secrets import Secret


def create_app_config() -> AppConfig:
    """
    Create AppConfig for local environment
    """
    # allow db endpoint (host:port) be overridden in docker compose
    dsj_db_endpoint: str = os.getenv("DSJ_DB_ENDPOINT", "localhost:5435")

    sentry_config = None
    if os.getenv("SENTRY_DSN", None):
        sentry_config = SentryConfig(
            dsn=Secret.from_env(name="sentry_dsn", env="SENTRY_DSN"),
            environment="local",
            release=f"payment-service@release-{os.getenv('RELEASE_TAG', 'unknown')}",
        )

    return AppConfig(
        ENVIRONMENT="local",
        DEBUG=False,  # Set this to True for debugging
        REMOTE_SECRET_ENABLED=False,
        API_STATSD_CONFIG=ApiStatsDConfig(
            TAGS={"service_name": "payment-service", "cluster": "local"}
        ),
        IDENTITY_SERVICE_HTTP_ENDPOINT="https://identity-service.doorcrawl.com",
        IDENTITY_SERVICE_GRPC_ENDPOINT="identity.doorcrawl-int.com:50051",
        PAYIN_SERVICE_ID=1631011374003906560,
        PAYOUT_SERVICE_ID=1631011374003906560,
        LEDGER_SERVICE_ID=1631011374003906560,
        TEST_SECRET=Secret(name="test_secret", value="hello_world_secret"),
        PAYIN_MAINDB_MASTER_URL=Secret(
            name="payin_maindb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYIN_MAINDB_REPLICA_URL=Secret(
            name="payin_maindb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYIN_PAYMENTDB_MASTER_URL=Secret(
            name="payin_paymentdb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        PAYIN_PAYMENTDB_REPLICA_URL=Secret(
            name="payin_paymentdb_url",
            value=f"postgresql://payin_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        PAYOUT_MAINDB_MASTER_URL=Secret(
            name="payout_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYOUT_MAINDB_REPLICA_URL=Secret(
            name="payout_maindb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/maindb_dev",
        ),
        PAYOUT_BANKDB_MASTER_URL=Secret(
            name="payout_bankdb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/bankdb_dev",
        ),
        PAYOUT_BANKDB_REPLICA_URL=Secret(
            name="payout_bankdb_url",
            value=f"postgresql://payout_user@{dsj_db_endpoint}/bankdb_dev",
        ),
        LEDGER_MAINDB_MASTER_URL=Secret(
            name="ledger_maindb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/maindb_dev",
        ),
        LEDGER_MAINDB_REPLICA_URL=Secret(
            name="ledger_maindb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/maindb_dev",
        ),
        LEDGER_PAYMENTDB_MASTER_URL=Secret(
            name="ledger_paymentdb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        LEDGER_PAYMENTDB_REPLICA_URL=Secret(
            name="ledger_paymentdb_url",
            value=f"postgresql://ledger_user@{dsj_db_endpoint}/paymentdb_dev",
        ),
        DEFAULT_DB_CONFIG=DBConfig(
            replica_pool_max_size=1, master_pool_max_size=5, debug=True
        ),
        AVAILABLE_MAINDB_REPLICAS=["maindb_dev"],
        STRIPE_US_SECRET_KEY=Secret(
            name="stripe_us_secret_key", value="sk_test_NH2ez5KKOx5qPWcNcFhjdr1R"
        ),
        STRIPE_US_PUBLIC_KEY=Secret(
            name="stripe_us_public_key", value="pk_test_NH2ez5KKOx5qPWcNcFhjdr1R"
        ),
        DSJ_API_BASE_URL="https://api.doorcrawl.com",
        DSJ_API_USER_EMAIL=Secret(name="dsj_api_user_email", value=""),
        DSJ_API_USER_PASSWORD=Secret(name="dsj_api_user_password", value=""),
        DSJ_API_JWT_TOKEN_TTL=1800,
        SENTRY_CONFIG=sentry_config,
        # don't need frequent monitoring for dev
        MONITOR_INTERVAL_EVENT_LOOP_LATENCY=10,
        MONITOR_INTERVAL_RESOURCE_JOB_POOL=10,
        # Payin
        CAPTURE_CRON_TRIGGER=CronTrigger(minute="*/2"),
    )
