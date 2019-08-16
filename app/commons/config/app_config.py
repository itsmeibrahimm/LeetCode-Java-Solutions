from dataclasses import dataclass
from typing import Dict, List, Optional

from typing_extensions import final

from app.commons.config.secrets import SecretAware, Secret


@final
@dataclass(frozen=True)
class SentryConfig(SecretAware):
    dsn: Secret
    environment: str
    release: str


@dataclass(frozen=True)
class DBConfig:
    debug: bool
    master_pool_max_size: int
    replica_pool_max_size: int
    master_pool_min_size: int = 1
    replica_pool_min_size: int = 1
    statement_timeout = 1.0
    force_rollback: bool = False

    def __post_init__(self):
        if self.master_pool_max_size <= 0:
            raise ValueError(
                f"master_pool_size should be > 0 but found={self.master_pool_max_size}"
            )
        if self.replica_pool_max_size <= 0:
            raise ValueError(
                f"replica_pool_size should be > 0 but found={self.replica_pool_max_size}"
            )
        if self.master_pool_min_size not in range(0, self.master_pool_max_size + 1):
            raise ValueError(
                f"master_pool_min_size should be within "
                f"[0, master_pool_max_size={self.master_pool_max_size}], but found {self.master_pool_min_size}"
            )
        if self.replica_pool_min_size not in range(0, self.replica_pool_max_size + 1):
            raise ValueError(
                f"replica_pool_min_size should be within "
                f"[0, replica_pool_max_size={self.replica_pool_max_size}], but found {self.replica_pool_min_size}"
            )


@final
@dataclass(frozen=True)
class AppConfig(SecretAware):
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
    REMOTE_SECRET_ENABLED: bool
    METRICS_CONFIG: Dict[str, str]

    # Test secret
    TEST_SECRET: Secret

    # DB configs
    PAYOUT_MAINDB_MASTER_URL: Secret
    PAYOUT_MAINDB_REPLICA_URL: Secret

    PAYOUT_BANKDB_MASTER_URL: Secret
    PAYOUT_BANKDB_REPLICA_URL: Secret

    PAYIN_MAINDB_MASTER_URL: Secret
    PAYIN_MAINDB_REPLICA_URL: Secret

    PAYIN_PAYMENTDB_MASTER_URL: Secret
    PAYIN_PAYMENTDB_REPLICA_URL: Secret

    LEDGER_MAINDB_MASTER_URL: Secret
    LEDGER_MAINDB_REPLICA_URL: Secret

    LEDGER_PAYMENTDB_MASTER_URL: Secret
    LEDGER_PAYMENTDB_REPLICA_URL: Secret

    DEFAULT_DB_CONFIG: DBConfig
    AVAILABLE_MAINDB_REPLICAS: List[str]

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
