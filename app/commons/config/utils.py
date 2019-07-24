import os
from typing import Callable, Mapping

from .app_config import AppConfig
from .local import create_app_config as LOCAL
from .prod import create_app_config as PROD
from .staging import create_app_config as STAGING
from .testing import create_app_config as TESTING

_CONFIG_MAP: Mapping[str, Callable[..., AppConfig]] = {
    "prod": PROD,
    "staging": STAGING,
    "local": LOCAL,
    "testing": TESTING,
}


def _get_app_config_by_environment() -> AppConfig:
    environment = os.getenv("ENVIRONMENT", None)
    assert environment is not None, (
        "ENVIRONMENT is not set through environment variable, "
        "valid ENVIRONMENT includes [prod, staging, local, testing]"
    )

    config_key = environment.lower()
    assert (
        config_key in _CONFIG_MAP
    ), f"Cannot find AppConfig specified by environment={config_key}"

    config_creator = _CONFIG_MAP[config_key]
    return config_creator()


def init_app_config() -> AppConfig:
    # TODO: add secrets loading code here
    return _get_app_config_by_environment()
