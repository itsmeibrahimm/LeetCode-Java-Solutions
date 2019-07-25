import os
from dataclasses import dataclass
from typing import Optional
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

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}-{self.name}-Ver[{self.version}]('**********')"
        )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}-{self.name}-Ver[{self.version}]('**********')"
        )

    @classmethod
    def from_env(cls, name: str, default: str = None):
        value = os.getenv(name, default)
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
    TODO: breakdown this to decouple paying/payout sub-app configs
    """

    DEBUG: bool
    NINOX_ENABLED: bool

    # Secret configurations start here
    TEST_SECRET: Secret
    PAYOUT_MAINDB_URL: Secret
    PAYOUT_BANKDB_URL: Secret
    PAYIN_MAINDB_URL: Secret
