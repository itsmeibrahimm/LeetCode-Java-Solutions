from typing import Any, cast

import pytest
import pytest_mock
from asynctest import MagicMock
from starlette.testclient import TestClient

from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.identity_client import StubbedIdentityClient
from app.commons.providers.stripe.stripe_client import StripeClient
from app.commons.providers.dsj_client import DSJClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.utils.pool import ThreadPoolHelper
from app.main import app


@pytest.fixture(autouse=True)
def client(mocker: pytest_mock.MockFixture, app_config: AppConfig):
    monitor = mocker.Mock()
    logger = mocker.Mock()
    payout_bankdb = mocker.Mock()
    payin_maindb = mocker.Mock()
    payin_paymentdb = mocker.Mock()
    payout_maindb = mocker.Mock()
    ledger_maindb = mocker.Mock()
    ledger_paymentdb = mocker.Mock()
    purchasecard_maindb = mocker.Mock()

    # fake context
    context = AppContext(
        monitor=monitor,
        log=logger,
        payout_maindb=payout_maindb,
        payout_bankdb=payout_bankdb,
        payin_maindb=payin_maindb,
        payin_paymentdb=payin_paymentdb,
        ledger_maindb=ledger_maindb,
        ledger_paymentdb=ledger_paymentdb,
        purchasecard_maindb=purchasecard_maindb,
        dsj_client=DSJClient(session=MagicMock(), client_config={}),
        identity_client=StubbedIdentityClient(),  # Does not matter
        stripe_thread_pool=ThreadPoolHelper(),
        stripe_client=StripeClient(
            settings_list=[
                models.StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ],
            http_client=TimedRequestsClient(),
        ),
        capture_service=MagicMock(),
        ids_session=MagicMock(),
        dsj_session=MagicMock(),
        marqeta_client=MagicMock(),
        marqeta_session=MagicMock(),
        redis_lock_manager=MagicMock(),
        redis_cluster=MagicMock(),
        kafka_producer=MagicMock(),
    )
    app.extra["context"] = cast(Any, context)

    # purposefully don't call startup/shutdown methods
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
