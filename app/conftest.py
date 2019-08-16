import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List
from uuid import uuid4

import factory
import pytest
from _pytest.nodes import Item
from pytest_mock import MockFixture
from starlette.testclient import TestClient

from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext, create_app_context
from app.commons.database.infra import DB
from app.commons.types import CountryCode, CurrencyType
from app.payin.core.cart_payment.model import PaymentIntent
from app.payin.core.cart_payment.types import (
    CaptureMethod,
    ConfirmationMethod,
    IntentStatus,
)
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository

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
async def app_context(app_config: AppConfig):
    return await create_app_context(app_config)


@pytest.fixture
async def payin_maindb(app_config: AppConfig):
    """
    initialize the maindb connection for PayIn user
    """
    async with DB.create(
        db_id="payin_maindb",
        db_config=app_config.DEFAULT_DB_CONFIG,
        master_url=app_config.PAYIN_MAINDB_MASTER_URL,
        replica_url=app_config.PAYIN_MAINDB_MASTER_URL,
    ) as db:
        yield db


@pytest.fixture
async def payout_maindb(app_config: AppConfig):
    """
    initialize the maindb connection for PayOut user
    """
    async with DB.create(
        db_id="payout_maindb",
        db_config=app_config.DEFAULT_DB_CONFIG,
        master_url=app_config.PAYOUT_MAINDB_MASTER_URL,
        replica_url=app_config.PAYOUT_MAINDB_MASTER_URL,
    ) as db:
        yield db


@pytest.fixture
async def payout_bankdb(app_config: AppConfig):
    """
    initialize the bankdb connection for PayOut user
    """
    async with DB.create(
        db_id="payout_bankdb",
        db_config=app_config.DEFAULT_DB_CONFIG,
        master_url=app_config.PAYOUT_BANKDB_MASTER_URL,
        replica_url=app_config.PAYOUT_BANKDB_MASTER_URL,
    ) as db:
        yield db


@pytest.fixture
async def ledger_paymentdb(app_config: AppConfig):
    """
    initialize the paymentdb connection for Ledger user
    """
    async with DB.create(
        db_id="ledger_paymentdb",
        db_config=app_config.DEFAULT_DB_CONFIG,
        master_url=app_config.LEDGER_PAYMENTDB_MASTER_URL,
        replica_url=app_config.LEDGER_PAYMENTDB_MASTER_URL,
    ) as db:
        yield db


@pytest.fixture
def dummy_app_context(mocker: MockFixture):
    return AppContext(
        log=mocker.Mock(),
        payout_bankdb=mocker.Mock(),
        payin_maindb=mocker.Mock(),
        payin_paymentdb=mocker.Mock(),
        payout_maindb=mocker.Mock(),
        ledger_maindb=mocker.Mock(),
        ledger_paymentdb=mocker.Mock(),
        stripe=mocker.Mock(),
        dsj_client=mocker.Mock(),
        identity_client=mocker.Mock(),
    )


@pytest.fixture
async def ledger_app_context(mocker: MockFixture, ledger_paymentdb: DB):
    return AppContext(
        log=mocker.Mock(),
        payout_bankdb=mocker.Mock(),
        payin_maindb=mocker.Mock(),
        payin_paymentdb=mocker.Mock(),
        payout_maindb=mocker.Mock(),
        ledger_maindb=mocker.Mock(),
        ledger_paymentdb=ledger_paymentdb,
        stripe=mocker.Mock(),
        dsj_client=mocker.Mock(),
        identity_client=mocker.Mock(),
    )


def pytest_collection_modifyitems(items: List[Item]):
    for item in items:
        # For all test cases placed under any .../test_integration/... path:
        # Dynamically add pytest.mark.integration to integration tests
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)


# REPOSITORIES


@pytest.fixture
async def cart_payment_repository(app_context: AppContext):
    return CartPaymentRepository(app_context)


@pytest.fixture
async def payer_repository(app_context: AppContext):
    yield PayerRepository(app_context)


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as client:
        yield client


# Factories


class PaymentIntentFactory(factory.Factory):
    class Meta:
        model = PaymentIntent

    id = factory.LazyAttribute(lambda o: str(uuid4()))
    cart_payment_id = factory.LazyAttribute(lambda o: str(uuid4()))
    idempotency_key = factory.LazyAttribute(lambda o: str(uuid4()))
    amount_initiated = 100
    amount = 100
    amount_capturable = 100
    amount_received = 0
    application_fee_amount = 0
    capture_method = CaptureMethod.MANUAL
    confirmation_method = ConfirmationMethod.MANUAL
    country = CountryCode.US
    currency = CurrencyType.USD
    status = IntentStatus.INIT
    statement_descriptor = str
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    captured_at = None
    cancelled_at = None
