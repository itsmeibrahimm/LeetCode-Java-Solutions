import os
import time
from abc import ABC
from dataclasses import dataclass, replace
from typing import Optional

from ninox.interface.helper import Helper
from typing_extensions import final

from app.commons.context.logger import init_logger as log


@final
@dataclass(frozen=True)
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


def init_ninox_client(config_section: str) -> Helper:
    ninox = Helper(config_section=config_section)
    if ninox.disabled:
        # Ninox helper internally set itself to disabled when init fails without raising exception.
        # We should fail fast here to prevent unknown service state at runtime.
        raise Helper.DisabledError("Ninox initialization failed")
    return ninox


def ninox_readiness_check() -> bool:
    """
    A blocking function call to check if ninox can be successfully initialized with retries.
    In prod, it currently could take up to 15 mins for a pod get IP assigned and being able to talk to kube2iam.
    !! this is only a workaround to allow worker processes start after ninox is ready !!
    """

    environment = os.environ.get("ENVIRONMENT", "unknown")
    if environment in ["prod", "staging"]:
        print(f"Start ninox readiness check for environment={environment}")

        timeout_sec = 15 * 60  # 15 mins.
        retry_interval_sec = 30
        max_retry = int(timeout_sec / retry_interval_sec)

        for attempt in range(1, max_retry + 1):
            print(f"checking ninox readiness attempt #{attempt}")
            try:
                init_ninox_client(config_section=environment)
                break
            except Exception as e:
                if attempt == max_retry:
                    raise ValueError(
                        f"Ninox was not ready within in {timeout_sec} seconds"
                    ) from e
                print(f"retry after {retry_interval_sec} seconds")
                time.sleep(retry_interval_sec)
        print(f"Ninox is ready")
    return True


class SecretLoader:
    """
    A secret loader class backed by Ninox. Fetches / refreshes actual secret value of a given Secret holder instance.

    Note: this can potentially be factored to an interface vending Secret instance without coupling on Ninox
    """

    ninox: Helper

    def __init__(self, *, environment: str):
        try:
            self.ninox = init_ninox_client(config_section=environment)
        except Exception:
            log.exception("ninox initialization failed")
            raise

    def fetch_secret(self, *, secret_holder: Secret) -> Secret:
        try:
            secret_val = str(
                self.ninox.get(secret_holder.name, version=secret_holder.version)
            )
        except Helper.SecretNotFoundError:
            raise Helper.SecretNotFoundError(f"secret={secret_holder} is not found")
        return replace(secret_holder, value=secret_val)


class SecretAware(ABC):
    """
    Marker interface for config objects containing secrets.
    An instance of any subclass of this interface should contain config values as Secret type
    """

    # if needed, we can potentially add additional sub namespace support here
    pass


def load_up_secret_aware_recursively(
    *, secret_aware: SecretAware, secret_loader: Optional[SecretLoader]
):

    for key in dir(secret_aware):
        item = secret_aware.__getattribute__(key)
        if isinstance(item, Secret) and item.value is None:
            if secret_loader:
                loaded_secret = secret_loader.fetch_secret(secret_holder=item)
                object.__setattr__(secret_aware, key, loaded_secret)
            else:
                if item.value is None:
                    raise KeyError(f"secret_holder={item} is not defined")
        elif isinstance(item, SecretAware):
            load_up_secret_aware_recursively(
                secret_aware=item, secret_loader=secret_loader
            )
