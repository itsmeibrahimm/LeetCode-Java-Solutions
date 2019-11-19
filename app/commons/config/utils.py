import os
from typing import Callable, Mapping

from app.commons.config.app_config import AppConfig
from app.commons.config.local import create_app_config as LOCAL
from app.commons.config.prod import create_app_config as PROD
from app.commons.config.prod import create_app_config_for_payin_cron as PAYIN_CRON_PROD
from app.commons.config.secrets import SecretLoader, load_up_secret_aware_recursively
from app.commons.config.staging import create_app_config as STAGING
from app.commons.config.staging import (
    create_app_config_for_payin_cron as PAYIN_CRON_STAGING,
)
from app.commons.config.testing import create_app_config as TESTING

_CONFIG_MAP_WEB: Mapping[str, Callable[..., AppConfig]] = {
    "prod": PROD,
    "staging": STAGING,
    "local": LOCAL,
    "testing": TESTING,
}


_CONFIG_MAP_PAYIN_CRON: Mapping[str, Callable[..., AppConfig]] = {
    "prod": PAYIN_CRON_PROD,
    "staging": PAYIN_CRON_STAGING,
    "local": LOCAL,
    "testing": TESTING,
}


def _init_app_config(config_map: Mapping[str, Callable[..., AppConfig]]) -> AppConfig:
    environment = os.getenv("ENVIRONMENT", None)
    assert environment is not None, (
        "ENVIRONMENT is not set through environment variable, "
        "valid ENVIRONMENT includes [prod, staging, local, testing]"
    )

    config_key = environment.lower()
    assert (
        config_key in config_map
    ), f"Cannot find AppConfig specified by environment={config_key}"

    app_config = config_map[config_key]()

    secret_loader = None
    if app_config.REMOTE_SECRET_ENABLED:
        secret_loader = SecretLoader(environment=config_key)

    load_up_secret_aware_recursively(
        secret_aware=app_config, secret_loader=secret_loader
    )

    return app_config


def init_app_config_for_web() -> AppConfig:
    return _init_app_config(_CONFIG_MAP_WEB)


def init_app_config_for_payin_cron() -> AppConfig:
    return _init_app_config(_CONFIG_MAP_PAYIN_CRON)
