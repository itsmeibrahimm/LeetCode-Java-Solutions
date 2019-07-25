import pytest

from starlette.testclient import TestClient
from app.payout.payout import app as payout_app


class TestAccounts:
    @pytest.fixture(autouse=True)
    def client(self):
        yield TestClient(payout_app)

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
