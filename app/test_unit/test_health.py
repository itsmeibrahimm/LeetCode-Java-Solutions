from typing import Any, cast

import pytest
import pytest_mock
from starlette.testclient import TestClient

from app.commons.context.app_context import AppContext
from app.commons.providers import stripe_models as models
from app.commons.providers.stripe_client import StripeClientPool
from app.commons.providers.dsj_client import DSJClient
from app.main import app


@pytest.fixture(autouse=True)
def client(mocker: pytest_mock.MockFixture):
    logger = mocker.Mock()
    payout_bankdb = mocker.Mock()
    payin_maindb = mocker.Mock()
    payin_paymentdb = mocker.Mock()
    payout_maindb = mocker.Mock()
    ledger_maindb = mocker.Mock()
    ledger_paymentdb = mocker.Mock()

    # fake context
    context = AppContext(
        log=logger,
        payout_maindb=payout_maindb,
        payout_bankdb=payout_bankdb,
        payin_maindb=payin_maindb,
        payin_paymentdb=payin_paymentdb,
        ledger_maindb=ledger_maindb,
        ledger_paymentdb=ledger_paymentdb,
        stripe=StripeClientPool(
            max_workers=5,
            settings_list=[
                models.StripeClientSettings(
                    api_key="sk_test_4eC39HqLyjWDarjtT1zdp7dc", country="US"
                )
            ],
        ),
        dsj_client=DSJClient({}),
    )
    app.extra["context"] = cast(Any, context)

    # purposefully don't call startup/shutdown methods
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
