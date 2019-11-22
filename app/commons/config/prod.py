import dataclasses
import os

import pytz
from apscheduler.triggers.cron import CronTrigger

from app.commons.config.app_config import (
    ApiStatsDConfig,
    AppConfig,
    DBConfig,
    SentryConfig,
)
from app.commons.config.secrets import Secret


def create_app_config() -> AppConfig:
    """
    Create AppConfig for prod environment
    """
    return AppConfig(
        INCLUDED_APPS=frozenset({"payout", "payin"}),
        ENVIRONMENT="prod",
        DEBUG=False,
        REMOTE_SECRET_ENABLED=True,
        STATSD_SERVER="prod-statsd-proxy.doordash.com",
        API_STATSD_CONFIG=ApiStatsDConfig(
            TAGS={"service_name": "payment-service", "cluster": "prod"}
        ),
        IDENTITY_SERVICE_HTTP_ENDPOINT="https://identity.doordash.com/",
        IDENTITY_SERVICE_GRPC_ENDPOINT="identity.int.doordash.com:50051",
        PAYIN_SERVICE_ID=1631011587067518976,
        PAYOUT_SERVICE_ID=1631011587067518976,
        LEDGER_SERVICE_ID=1631011587067518976,
        PURCHASECARD_SERVICE_ID=1631011587067518976,
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
        PURCHASECARD_MAINDB_MASTER_URL=Secret(name="purchasecard_maindb_url"),
        PURCHASECARD_MAINDB_REPLICA_URL=Secret(name="purchasecard_maindb_replica_url"),
        DEFAULT_DB_CONFIG=DBConfig(
            replica_pool_max_size=5,
            master_pool_max_size=5,
            debug=False,
            # set to 10 sec to avoid thrashing DB server on client side
            # highest p99 latency from payment service around 10sec: https://metrics.wavefront.com/u/YWSfZCttKN
            statement_timeout_sec=10,
        ),
        AVAILABLE_MAINDB_REPLICAS=[
            "doordash_replica1",
            "doordash_replica2",
            "doordash_replica3",
            "doordash_replica4",
        ],
        STRIPE_US_SECRET_KEY=Secret(name="stripe_us_secret_key"),
        STRIPE_US_PUBLIC_KEY=Secret(name="stripe_us_public_key"),
        STRIPE_CA_SECRET_KEY=Secret(name="stripe_ca_secret_key"),
        STRIPE_CA_PUBLIC_KEY=Secret(name="stripe_ca_public_key"),
        STRIPE_AU_SECRET_KEY=Secret(name="stripe_au_secret_key"),
        STRIPE_AU_PUBLIC_KEY=Secret(name="stripe_au_public_key"),
        DSJ_API_BASE_URL="https://api.doordash.com",
        DSJ_API_USER_EMAIL=Secret(name="dsj_api_user_email"),
        DSJ_API_USER_PASSWORD=Secret(name="dsj_api_user_password"),
        DSJ_API_JWT_TOKEN_TTL=1800,
        SENTRY_CONFIG=SentryConfig(
            dsn=Secret(name="sentry_dsn"),
            environment="prod",
            release=f"payment-service@release-{os.getenv('RELEASE_TAG')}",
        ),
        # exclude 16:00 - 18:00 pacific time 3 hourly triggers to avoid US peak hour
        CAPTURE_CRON_TRIGGER=CronTrigger(
            hour="0-15,19-23", minute="*/15", timezone=pytz.timezone("US/Pacific")
        ),
        DEFAULT_CAPTURE_DELAY_IN_MINUTES=180,  # 180 mins
        MARQETA_BASE_URL="https://doordash-api.marqeta.com/v3/",
        MARQETA_USERNAME=Secret(name="marqeta_username"),
        MARQETA_PASSWORD=Secret(name="marqeta_password"),
        MARQETA_JIT_USERNAME=Secret(name="marqeta_jit_username"),
        MARQETA_JIT_PASSWORD=Secret(name="marqeta_jit_password"),
        MARQETA_PROGRAM_FUND_TOKEN=Secret(name="marqeta_program_fund_token"),
        # currently using merchant_datastore redis instance, which is the same as the one used for payment in DSJ
        # better to switch to payment's own redis instance after instant payout/transfer migration
        REDIS_INSTANCES=[
            ("prod-default-d.mhazzc.ng.0001.usw2.cache.amazonaws.com", 6379)
        ],
    )


def create_app_config_for_payin_cron() -> AppConfig:
    web_appconfig = create_app_config()
    return dataclasses.replace(web_appconfig, STRIPE_MAX_WORKERS=30)
