import os
from typing import Callable, Mapping

from app.commons.config.app_config import AppConfig
from app.commons.config.local import create_app_config as LOCAL
from app.commons.config.prod import create_app_config as PROD
from app.commons.config.secrets import SecretLoader, load_up_secret_aware_recursively
from app.commons.config.staging import create_app_config as STAGING
from app.commons.config.testing import create_app_config as TESTING

_CONFIG_MAP: Mapping[str, Callable[..., AppConfig]] = {
    "prod": PROD,
    "staging": STAGING,
    "local": LOCAL,
    "testing": TESTING,
}


def init_app_config() -> AppConfig:
    environment = os.getenv("ENVIRONMENT", None)
    assert environment is not None, (
        "ENVIRONMENT is not set through environment variable, "
        "valid ENVIRONMENT includes [prod, staging, local, testing]"
    )

    config_key = environment.lower()
    assert (
        config_key in _CONFIG_MAP
    ), f"Cannot find AppConfig specified by environment={config_key}"

    app_config = _CONFIG_MAP[config_key]()

    secret_loader = None
    if app_config.REMOTE_SECRET_ENABLED:
        secret_loader = SecretLoader(environment=config_key)

    load_up_secret_aware_recursively(
        secret_aware=app_config, secret_loader=secret_loader
    )

    return app_config
