import os
from typing import Mapping

from .app_config import AppConfig
from .local import LOCAL
from .prod import PROD
from .staging import STAGING

_CONFIG_MAP: Mapping[str, AppConfig] = {
    "prod": PROD,
    "staging": STAGING,
    "local": LOCAL,
}


def _get_app_config_by_environment() -> AppConfig:
    environment = os.getenv("ENVIRONMENT", None)
    assert environment is not None, (
        "ENVIRONMENT is not set through environment variable, "
        "valid ENVIRONMENT includes [prod, staging, local]"
    )

    config_key = environment.lower()
    assert (
        config_key in _CONFIG_MAP
    ), f"Cannot find AppConfig specified by environment={config_key}"

    return _CONFIG_MAP[config_key]


def init_app_config() -> AppConfig:
    # TODO: add secrets loading code here
    return _get_app_config_by_environment()
