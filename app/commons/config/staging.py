import dataclasses
import os

from app.commons.config.app_config import (
    AppConfig,
    ApiStatsDConfig,
    DBConfig,
    SentryConfig,
)
from app.commons.config.secrets import Secret
from apscheduler.triggers.cron import CronTrigger


def create_app_config() -> AppConfig:
    """
    Create AppConfig for staging environment
    """
    return AppConfig(
        ENVIRONMENT="staging",
        DEBUG=False,
        REMOTE_SECRET_ENABLED=True,
        STATSD_SERVER="staging-statsd-proxy.doorcrawl-int.com",
        API_STATSD_CONFIG=ApiStatsDConfig(
            TAGS={"service_name": "payment-service", "cluster": "staging"}
        ),
        IDENTITY_SERVICE_HTTP_ENDPOINT="http://identity-service-helm-web.staging",
        IDENTITY_SERVICE_GRPC_ENDPOINT="identity.doorcrawl-int.com:50051",
        PAYIN_SERVICE_ID=1631011374003906560,
        PAYOUT_SERVICE_ID=1631011374003906560,
        LEDGER_SERVICE_ID=1631011374003906560,
        PURCHASECARD_SERVICE_ID=1631011374003906560,
        TEST_SECRET=Secret(name="hello_world_secret"),
        PAYIN_MAINDB_MASTER_URL=Secret(name="payin_maindb_url"),
        PAYIN_MAINDB_REPLICA_URL=Secret(name="payin_maindb_replica_url"),
        PAYIN_PAYMENTDB_MASTER_URL=Secret(name="payin_paymentdb_url"),
        PAYIN_PAYMENTDB_REPLICA_URL=Secret(name="payin_paymentdb_replica_url"),
        PAYOUT_MAINDB_MASTER_URL=Secret(name="payout_maindb_url"),
        PAYOUT_MAINDB_REPLICA_URL=Secret(name="payout_maindb_replica_url"),
        PAYOUT_BANKDB_MASTER_URL=Secret(name="payout_bankdb_url"),
        PAYOUT_BANKDB_REPLICA_URL=Secret(name="payout_bankdb_replica_url"),
        LEDGER_MAINDB_MASTER_URL=Secret(name="ledger_maindb_url"),
        LEDGER_MAINDB_REPLICA_URL=Secret(name="ledger_maindb_replica_url"),
        LEDGER_PAYMENTDB_MASTER_URL=Secret(name="ledger_paymentdb_url"),
        LEDGER_PAYMENTDB_REPLICA_URL=Secret(name="ledger_paymentdb_replica_url"),
        PURCHASECARD_MAINDB_MASTER_URL=Secret(name="purchasecard_maindb_url"),
        PURCHASECARD_MAINDB_REPLICA_URL=Secret(name="purchasecard_maindb_replica_url"),
        PURCHASECARD_PAYMENTDB_MASTER_URL=Secret(name="purchasecard_paymentdb_url"),
        PURCHASECARD_PAYMENTDB_REPLICA_URL=Secret(name="purchasecard_paymentdb_url"),
        DEFAULT_DB_CONFIG=DBConfig(
            replica_pool_max_size=5,
            master_pool_max_size=5,
            debug=False,
            # set to 10 sec to avoid thrashing DB server on client side
            # highest p99 latency from payment service around 10sec: https://metrics.wavefront.com/u/YWSfZCttKN
            statement_timeout_sec=10,
        ),
        AVAILABLE_MAINDB_REPLICAS=[],
        STRIPE_US_SECRET_KEY=Secret(
            name="stripe_us_secret_key", value="sk_test_NH2ez5KKOx5qPWcNcFhjdr1R"
        ),
        STRIPE_US_PUBLIC_KEY=Secret(
            name="stripe_us_public_key", value="pk_test_VCKL0VKIMMPzuUB8ZbuXdKkA"
        ),
        STRIPE_CA_SECRET_KEY=Secret(
            name="stripe_ca_secret_key", value="sk_test_DjN82k53PAi4mKVlkeOXUsGh"
        ),
        STRIPE_CA_PUBLIC_KEY=Secret(
            name="stripe_ca_public_key", value="pk_test_6BIBosD7fUMQKx5ehGg5L6pz"
        ),
        STRIPE_AU_SECRET_KEY=Secret(
            name="stripe_au_secret_key",
            value="sk_test_kwb7Pky1rEyIYbWhIBnHbEG500GIVp7eeO",
        ),
        STRIPE_AU_PUBLIC_KEY=Secret(
            name="stripe_au_public_key",
            value="pk_test_dJ998ZEOQNHLDCAQG37EKbId00c9TVHvH7",
        ),
        DSJ_API_BASE_URL="https://api.doorcrawl.com",
        DSJ_API_USER_EMAIL=Secret(name="dsj_api_user_email"),
        DSJ_API_USER_PASSWORD=Secret(name="dsj_api_user_password"),
        DSJ_API_JWT_TOKEN_TTL=1800,
        SENTRY_CONFIG=SentryConfig(
            dsn=Secret(name="sentry_dsn"),
            environment="staging",
            release=f"payment-service@release-{os.getenv('RELEASE_TAG')}",
        ),
        MARQETA_BASE_URL="https://doordash-dev.marqeta.com/v3/",
        MARQETA_USERNAME=Secret(
            name="marqeta_username", value="doordash_sandbox_api_consumer"
        ),
        MARQETA_PASSWORD=Secret(
            name="marqeta_password", value="80ffbbe4-f68c-43e8-a256-f6d14d818ef2"
        ),
        MARQETA_JIT_USERNAME=Secret(name="marqeta_jit_username", value=""),
        MARQETA_JIT_PASSWORD=Secret(name="marqeta_jit_password", value=""),
        MARQETA_PROGRAM_FUND_TOKEN=Secret(
            name="marqeta_program_fund_token",
            value="a6e2bbe7-4f28-43b4-980d-6416f35fe33e",
        ),
        CAPTURE_CRON_TRIGGER=CronTrigger(hour="0-23", minute="*/15"),
        MARQETA_CARD_TOKEN_PREFIX_CUTOVER_ID=Secret(
            name="marqeta_card_token_prefix_cutover_id", value="73617"
        ),
        # currently using merchant_datastore redis instance, which is the same as the one used for payment in DSJ
        # better to switch to payment's own redis instance after instant payout/transfer migration
        REDIS_INSTANCES=[("staging0.trwaqb.0001.usw2.cache.amazonaws.com", 6379)],
        # todo: Get Kafka staging URL
        KAFKA_URL="localhost:9092",
        REDIS_CLUSTER_INSTANCES=[
            {
                "host": "staging-payment-service-cluster.trwaqb.clustercfg.usw2.cache.amazonaws.com",
                "port": 6379,
            }
        ],
    )


def create_app_config_for_payin_cron() -> AppConfig:
    web_appconfig = create_app_config()
    return dataclasses.replace(
        web_appconfig, STRIPE_MAX_WORKERS=60, PAYIN_CRON_JOB_POOL_DEFAULT_SIZE=40
    )


def create_app_config_for_payout_cron() -> AppConfig:
    web_appconfig = create_app_config()
    return dataclasses.replace(
        web_appconfig, STRIPE_MAX_WORKERS=30, PAYOUT_CRON_JOB_POOL_DEFAULT_SIZE=30
    )
