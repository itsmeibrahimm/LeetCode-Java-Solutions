import os
from dataclasses import dataclass
from typing import Dict, Optional

from typing_extensions import final


@final
@dataclass
class Secret:
    """
    Holds a string secret config value that should not be revealed in logging and etc.
    """

    name: str
    version: Optional[int] = None
    value: Optional[str] = None

    def __post_init__(self):
        assert self.name.islower(), "name of secret should always be lower cased"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}-{self.name}-Ver[{self.version}]('**********')"
        )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}-{self.name}-Ver[{self.version}]('**********')"
        )

    @classmethod
    def from_env(cls, name: str, env: str, default: str = None):
        value = os.getenv(env, default)
        if value is None:
            raise KeyError(f"Environment variable={name} not defined")
        return cls(name=name, version=None, value=value)


@final
@dataclass(frozen=True)
class AppConfig:
    """
    A config class contains all necessary config key-values to bootstrap application.
    For local/staging/prod application environments, there are corresponding instances
    of this _Config class:
    - local: local.py::LOCAL
    - staging: staging.py::STAGING
    - prod: prod.py::PROD
    """

    ENVIRONMENT: str
    DEBUG: bool
    NINOX_ENABLED: bool
    METRICS_CONFIG: Dict[str, str]

    # Test secret
    TEST_SECRET: Secret

    # DB configs
    PAYOUT_MAINDB_URL: Secret
    PAYOUT_BANKDB_URL: Secret
    PAYIN_MAINDB_URL: Secret
    PAYIN_PAYMENTDB_URL: Secret
    LEDGER_MAINDB_URL: Secret
    LEDGER_PAYMENTDB_URL: Secret

    # Payment Service Provider
    STRIPE_US_SECRET_KEY: Secret
    STRIPE_US_PUBLIC_KEY: Secret

    STATSD_SERVER: str = "prod-proxy-internal.doordash.com"
    STATSD_PREFIX: str = "payment-service"
    STRIPE_MAX_WORKERS: int = 10
