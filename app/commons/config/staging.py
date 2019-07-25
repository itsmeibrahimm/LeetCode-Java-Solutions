from app.commons.config.app_config import AppConfig, Secret


def create_app_config() -> AppConfig:
    """
    Configurations loaded to Flask App.config dictionary when ENVIRONMENT=staging
    """
    return AppConfig(
        DEBUG=False,
        NINOX_ENABLED=True,
        # Secret configurations start here
        TEST_SECRET=Secret(name="hello_world_secret"),
        PAYIN_MAINDB_URL=Secret(name="payin_maindb_url"),
        PAYOUT_MAINDB_URL=Secret(name="payout_maindb_url"),
        PAYOUT_BANKDB_URL=Secret(name="payout_bankdb_url"),
    )
