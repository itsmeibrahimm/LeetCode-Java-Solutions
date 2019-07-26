import pytest
import pytest_mock

from typing import Any, cast
from starlette.testclient import TestClient
from gino import Gino
from app.commons.context.app_context import AppContext
from app.payout.payout import create_payout_app


class TestAccounts:
    @pytest.fixture(autouse=True)
    def client(
        self,
        mocker: pytest_mock.MockFixture,
        # payin_maindb: Gino,
        # payout_maindb: Gino,
        # payout_bankdb: Gino,
    ):
        logger = mocker.Mock()
        # payout_maindb_master = payout_maindb
        # payout_bankdb_master = payout_bankdb
        # payin_maindb_master = payin_maindb
        payout_maindb_master = Gino()
        payout_bankdb_master = Gino()
        payin_maindb_master = Gino()
        context = AppContext(
            logger, payout_maindb_master, payout_bankdb_master, payin_maindb_master
        )
        app = create_payout_app(context)
        app.extra["context"] = cast(Any, context)
        yield TestClient(app)

    def test_invalid(self, client: TestClient):
        response = client.get("/accounts/")
        assert response.status_code == 405, "accessing accounts requires an id"

    @pytest.mark.skip(reason="database connection not available")
    def test_create(self, client: TestClient):
        response = client.post(
            "/accounts/",
            json={
                "statement_descriptor": "yup",
                "account_type": "blah",
                "entity": "entity",
            },
        )
        assert response.status_code == 200
