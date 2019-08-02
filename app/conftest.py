import os
from dataclasses import dataclass
from typing import Any

import pytest

from app.commons.config.app_config import AppConfig
from app.commons.database.model import Database

os.environ["ENVIRONMENT"] = "testing"


@dataclass(frozen=True)
class StripeAPISettings:
    stripe: Any
    # see: https://github.com/stripe/stripe-python/blob/master/tests/conftest.py
    # for a list of settings to reset between tests
    api_base: str
    api_key: str
    client_id: str
    default_http_client: Any
    verify_ssl_certs: bool

    @classmethod
    def init_from_stripe(cls, stripe):
        return cls(
            stripe=stripe,
            api_base=stripe.api_base,
            api_key=stripe.api_key,
            client_id=stripe.client_id,
            default_http_client=stripe.default_http_client,
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
        self.stripe.api_key = self.api_key
        self.stripe.client_id = self.stripe.client_id
        self.stripe.default_http_client = self.default_http_client
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
async def payin_maindb(app_config: AppConfig):
    """
    initialize the maindb connection for PayIn user
    """
    db = await Database.from_url(master_url=app_config.PAYIN_MAINDB_URL)
    yield db
    await db.close()


@pytest.fixture
async def payout_maindb(app_config: AppConfig):
    """
    initialize the maindb connection for PayOut user
    """
    db = await Database.from_url(master_url=app_config.PAYOUT_MAINDB_URL)
    yield db
    await db.close()


@pytest.fixture
async def payout_bankdb(app_config: AppConfig):
    """
    initialize the bankdb connection for PayOut user
    """
    db = await Database.from_url(master_url=app_config.PAYOUT_BANKDB_URL)
    yield db
    await db.close()
