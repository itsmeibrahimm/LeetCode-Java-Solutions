from .app_config import AppConfig, Secret


def create_app_config() -> AppConfig:
    return AppConfig(
        DEBUG=True,
        NINOX_ENABLED=False,
        METRICS_CONFIG={"service_name": "payment-service", "cluster": "testing"},
        # Secret configurations start here
        TEST_SECRET=Secret.from_env("TEST_SECRET", "hello_world_secret"),
        PAYIN_MAINDB_URL=Secret.from_env(
            "PAYIN_MAINDB_URL", "postgresql://payin_user@localhost/maindb_test"
        ),
        PAYOUT_MAINDB_URL=Secret.from_env(
            "PAYOUT_MAINDB_URL", "postgresql://payout_user@localhost/maindb_test"
        ),
        PAYOUT_BANKDB_URL=Secret.from_env(
            "PAYOUT_BANKDB_URL", "postgresql://payout_user@localhost/bankdb_test"
        ),
    )
