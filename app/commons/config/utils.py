import dataclasses
import os
from typing import Callable, Mapping

from ninox.interface.helper import Helper

from app.commons.config.app_config import AppConfig, Secret
from app.commons.config.local import create_app_config as LOCAL
from app.commons.config.prod import create_app_config as PROD
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

    if app_config.NINOX_ENABLED:
        ninox = Helper(config_section=environment)
        if ninox.disabled:
            # Ninox helper internally set itself to disabled when init fails without raising exception.
            # We should fail fast here to prevent unknown service state at runtime.
            raise Helper.DisabledError("Ninox initialization failed")

        for key in dir(app_config):
            config = app_config.__getattribute__(key)
            if isinstance(config, Secret):
                try:
                    secret_val = str(ninox.get(config.name, version=config.version))
                except Helper.SecretNotFoundError:
                    raise Helper.SecretNotFoundError(
                        f"config name={config.name} is not found"
                    )
                updated_secret_config = dataclasses.replace(config, value=secret_val)
                object.__setattr__(app_config, key, updated_secret_config)

    else:
        # When working with Ninox disabled, should also make sure all "secrets" are actually configured
        for key in dir(app_config):
            config = app_config.__getattribute__(key)
            if isinstance(config, Secret):
                if config.value is None:
                    raise KeyError(f"config name={config.name} is not defined")

    return app_config
