import os
from dataclasses import dataclass
from typing import Dict, Optional

from typing_extensions import final

from app.commons.database.config import DatabaseConfig


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
class SentryConfig:
    dsn: Secret
    environment: str
    release: str


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
    PAYOUT_MAINDB_MASTER_URL: Secret
    PAYOUT_MAINDB_REPLICA_URL: Optional[Secret]

    PAYOUT_BANKDB_MASTER_URL: Secret
    PAYOUT_BANKDB_REPLICA_URL: Optional[Secret]

    PAYIN_MAINDB_MASTER_URL: Secret
    PAYIN_MAINDB_REPLICA_URL: Optional[Secret]

    PAYIN_PAYMENTDB_MASTER_URL: Secret
    PAYIN_PAYMENTDB_REPLICA_URL: Optional[Secret]

    LEDGER_MAINDB_MASTER_URL: Secret
    LEDGER_MAINDB_REPLICA_URL: Optional[Secret]

    LEDGER_PAYMENTDB_MASTER_URL: Secret
    LEDGER_PAYMENTDB_REPLICA_URL: Optional[Secret]

    DEFAULT_DB_CONFIG: DatabaseConfig

    # Payment Service Provider
    STRIPE_US_SECRET_KEY: Secret
    STRIPE_US_PUBLIC_KEY: Secret

    # DSJ client
    DSJ_API_USER_EMAIL: Secret
    DSJ_API_USER_PASSWORD: Secret
    DSJ_API_BASE_URL: str = "https://api.doordash.com"
    DSJ_API_JWT_TOKEN_TTL: int = 1800  # in seconds

    STATSD_SERVER: str = "prod-proxy-internal.doordash.com"
    STATSD_PREFIX: str = "payment-service"

    SENTRY_CONFIG: Optional[SentryConfig] = None

    STRIPE_MAX_WORKERS: int = 10
