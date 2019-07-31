from typing import Any, cast

import pytest
import pytest_mock
from gino import Gino
from starlette.testclient import TestClient

from app.commons.context.app_context import AppContext
from app.commons.providers.stripe_client import StripeClientPool
from app.commons.providers import stripe_models as models
from app.main import app


@pytest.fixture(autouse=True)
def client(mocker: pytest_mock.MockFixture):
    logger = mocker.Mock()
    payout_maindb_master = Gino()
    payout_bankdb_master = Gino()
    payin_maindb_master = Gino()
    payin_paymentdb_master = Gino()

    # fake context
    context = AppContext(
        log=logger,
        payout_maindb_master=payout_maindb_master,
        payout_bankdb_master=payout_bankdb_master,
        payin_maindb_master=payin_maindb_master,
        payin_paymentdb_master=payin_paymentdb_master,
        stripe=StripeClientPool(
            max_workers=5,
            settings_list=[
                models.StripeClientSettings(
                    api_key="sk_test_4eC39HqLyjWDarjtT1zdp7dc", country="US"
                )
            ],
        ),
    )
    app.extra["context"] = cast(Any, context)

    # purposefully don't call startup/shutdown methods
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
