from dataclasses import dataclass
from typing import Any
import os
import pytest
from gino import Gino
from app.commons.config.app_config import AppConfig

os.environ["ENVIRONMENT"] = "testing"


@dataclass(frozen=True)
class StripeAPISettings:
    stripe: Any
    api_base: str
    verify_ssl_certs: bool

    @classmethod
    def init_from_stripe(cls, stripe):
        return cls(
            stripe=stripe,
            api_base=stripe.api_base,
            verify_ssl_certs=stripe.verify_ssl_certs,
        )

    def disable_outbound(self):
        self.stripe.api_base = "http://localhost"
        self.stripe.verify_ssl_certs = False

    def enable_mock(self):
        self.stripe.api_base = os.environ.get(
            "STRIPE_API_BASE", "http://localhost:12111"
        )
        self.stripe.verify_ssl_certs = False

    def enable_outbound(self):
        self.restore()

    def restore(self):
        self.stripe.api_base = self.api_base
        self.stripe.verify_ssl_certs = self.verify_ssl_certs


@pytest.fixture(autouse=True)
def stripe_api():
    """
    disallow stripe access from tests, unless specifically enabled
    """
    import stripe

    api_settings = StripeAPISettings.init_from_stripe(stripe)
    # disable outbound access by pointing to localhost
    api_settings.disable_outbound()
    yield api_settings
    # restore default api settings
    api_settings.restore()


@pytest.fixture
def app_config():
    from app.commons.config.utils import init_app_config

    return init_app_config()


@pytest.fixture
async def payin_maindb(app_config: AppConfig) -> Gino:
    """
    initialize the maindb connection for PayIn user
    """
    db = await Gino(app_config.PAYIN_MAINDB_URL.value)
    yield db
    await db.pop_bind().close()


@pytest.fixture
async def payout_maindb(app_config: AppConfig) -> Gino:
    """
    initialize the maindb connection for PayOut user
    """
    db = await Gino(app_config.PAYOUT_MAINDB_URL.value)
    yield db
    await db.pop_bind().close()


@pytest.fixture
async def payout_bankdb(app_config: AppConfig) -> Gino:
    """
    initialize the bankdb connection for PayOut user
    """
    db = await Gino(app_config.PAYOUT_BANKDB_URL.value)
    yield db
    await db.pop_bind().close()
