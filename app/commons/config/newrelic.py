from dataclasses import dataclass
from app.commons.config.secrets import (
    Secret,
    SecretAware,
    SecretLoader,
    load_up_secret_aware_recursively,
)


@dataclass
class NewRelicConfig(SecretAware):
    NEW_RELIC_LICENSE_KEY: Secret


def create_new_relic_config(environment) -> NewRelicConfig:
    # only fetch ninox secrets in prod/staging
    if environment in ["prod", "staging"]:
        secret_loader = SecretLoader(environment=environment)
        config = NewRelicConfig(
            NEW_RELIC_LICENSE_KEY=Secret(name="new_relic_license_key")
        )
        load_up_secret_aware_recursively(
            secret_aware=config, secret_loader=secret_loader
        )
    else:
        config = NewRelicConfig(
            NEW_RELIC_LICENSE_KEY=Secret(
                name="new_relic_license_key", value="license-key"
            )
        )

    return config
