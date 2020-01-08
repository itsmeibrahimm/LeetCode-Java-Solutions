import json
import os
import unittest.mock
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple, Union
from unittest.mock import Mock

import pytest
from _pytest.nodes import Item
from doordash_python_stats.ddstats import DoorStatsProxyMultiServer
from pytest_mock import MockFixture
from starlette.testclient import TestClient

from app.commons import stats
from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext, create_app_context
from app.commons.context.logger import get_logger
from app.commons.database.infra import DB
from app.commons.utils.testing import Stat, parse_raw_stat

os.environ["ENVIRONMENT"] = "testing"

stats_logger = get_logger("statsd")

RuntimeTypes = Union[Dict, List, Tuple, bool, str, int, float]


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


@pytest.fixture(autouse=True)
def global_statsd_client():
    """
    always initialize the global statsd client
    """
    from doordash_python_stats import ddstats
    from app.commons.stats import init_global_statsd

    init_global_statsd(
        prefix="dd.pay.payment-service", host="localhost", fixed_tags={"env": "local"}
    )
    yield ddstats.doorstats_global


@pytest.fixture
def service_statsd_client():
    statsd_client = DoorStatsProxyMultiServer()
    statsd_client.initialize(prefix="dd.pay.payment-service", host="localhost")
    with stats.set_service_stats_client(statsd_client):
        yield statsd_client


@pytest.fixture(autouse=True)
def mock_statsd_client(mocker: MockFixture):
    """
    prevent stats from actually being sent out in tests
    """

    def _send(data):
        stats_logger.info("statsd: sending: %s", data)

    return mocker.patch("statsd.StatsClient._send", side_effect=_send)


@pytest.fixture
def get_mock_statsd_events(mock_statsd_client: Mock) -> Callable[[], List[Stat]]:
    def get():
        stats: List[Stat] = []
        for args, _ in mock_statsd_client.call_args_list:
            stat = parse_raw_stat(args[0])
            if stat:
                stats.append(stat)
        return stats

    return get


@pytest.fixture
def reset_mock_statsd_events(mock_statsd_client: Mock) -> Callable[[], None]:
    def reset():
        mock_statsd_client.reset_mock()

    return reset


@pytest.fixture
def app_config():
    from app.commons.config.utils import init_app_config_for_web

    return init_app_config_for_web()


@pytest.fixture
async def app_context(app_config: AppConfig):
    context = await create_app_context(app_config)
    yield context
    await context.close()


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
async def purchasecard_maindb(app_config: AppConfig):
    """
    initialize the maindb connection for PurchaseCard user
    """
    async with DB.create(
        db_id="purchasecard_maindb",
        db_config=app_config.DEFAULT_DB_CONFIG,
        master_url=app_config.PURCHASECARD_MAINDB_MASTER_URL,
        replica_url=app_config.PURCHASECARD_MAINDB_MASTER_URL,
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
async def purchasecard_paymentdb(app_config: AppConfig):
    """
    initialize the paymentdb connection for Ledger user
    """
    async with DB.create(
        db_id="purchasecard_paymentdb",
        db_config=app_config.DEFAULT_DB_CONFIG,
        master_url=app_config.PURCHASECARD_PAYMENTDB_MASTER_URL,
        replica_url=app_config.PURCHASECARD_PAYMENTDB_MASTER_URL,
    ) as db:
        yield db


@pytest.fixture
def dummy_app_context(mocker: MockFixture):
    return AppContext(
        monitor=mocker.Mock(),
        log=mocker.Mock(),
        payout_bankdb=mocker.Mock(),
        payin_maindb=mocker.Mock(),
        payin_paymentdb=mocker.Mock(),
        payout_maindb=mocker.Mock(),
        ledger_maindb=mocker.Mock(),
        ledger_paymentdb=mocker.Mock(),
        purchasecard_maindb=mocker.Mock(),
        purchasecard_paymentdb=mocker.Mock(),
        dsj_client=mocker.Mock(),
        identity_client=mocker.Mock(),
        stripe_thread_pool=mocker.Mock(),
        stripe_client=mocker.Mock(),
        capture_service=mocker.Mock(),
        ids_session=mocker.Mock(),
        dsj_session=mocker.Mock(),
        marqeta_client=mocker.Mock(),
        marqeta_session=mocker.Mock(),
        redis_lock_manager=mocker.Mock(),
        redis_cluster=mocker.Mock(),
        kafka_producer=mocker.Mock(),
    )


def pytest_collection_modifyitems(items: List[Item]):
    for item in items:
        # For all test cases placed under any .../test_integration/... path:
        # Dynamically add pytest.mark.integration to integration tests
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def runtime_setter():
    with RuntimeSetter() as runtime_setter:
        yield runtime_setter


class RuntimeSetter(object):
    """
    Used for setting runtime values for tests. Retrieve it using the runtime_setter fixture.

    Example:
        def test(runtime_setter):
            runtime_setter.set('YOLO', True)

    OR explicitly used

        with RuntimeSetter() as runtime_setter:
            ...
    """

    def __init__(self):
        self._overrides: Dict[str, RuntimeTypes] = {}
        self._patched_get_content: unittest.mock._patch = unittest.mock.patch(
            "app.commons.runtime.runtime.get_content", side_effect=self._get_content
        )

    def __enter__(self):
        self._patched_get_content.start()
        return self

    def __exit__(self, type, value, traceback):
        self._patched_get_content.stop()

    def set(self, filename: str, content: RuntimeTypes):
        if isinstance(content, dict) or isinstance(content, (list, tuple)):
            content_str = json.dumps(content)
        else:
            content_str = str(content)

        self._overrides[filename] = content_str

    def remove(self, filename: str):
        del self._overrides[filename]

    def get(self, filename: str):
        return self._overrides.get(filename, None)

    def _get_content(self, file_name: str):
        return self.overrides.get(file_name, None)

    @property
    def overrides(self):
        return self._overrides


class RuntimeContextManager:
    """
    TODO: figure out how to make this more fool proof
    Utility for managing the state of a runtime value within a context for tests

    Usage:

    with RuntimeContextManager("cold_sandwich", True, runtime_setter) as manager:
        ...

    NOTE: runtime_setter should be coming from the fixture provided from pytest conf files.
    """

    def __init__(self, key: str, val: Any, runtime_setter: RuntimeSetter):
        self.key = key
        self.val = val
        self.runtime_setter = runtime_setter

    def __enter__(self):
        self.old_value = self.runtime_setter.get(self.key)
        self.runtime_setter.set(self.key, self.val)

    def __exit__(self, type, value, traceback):
        if self.old_value:
            self.runtime_setter.set(self.key, self.old_value)
        else:
            self.runtime_setter.remove(self.key)
