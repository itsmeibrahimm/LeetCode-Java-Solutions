import pytest
from starlette.testclient import TestClient

from app.main import app


class TestAccounts:
    pytestmark = [pytest.mark.integration]

    @pytest.fixture(autouse=True, scope="class")
    def client(self):
        with TestClient(app) as client:
            yield client

    @pytest.mark.skip("skip until v0 account API created")
    def test_invalid(self, client: TestClient):
        response = client.get("/payout/accounts/")
        assert response.status_code == 405, "accessing accounts requires an id"

    @pytest.mark.skip("skip until v0 account API created")
    def test_create(self, client: TestClient):
        response = client.post(
            "/payout/accounts/",
            json={
                "statement_descriptor": "yup",
                "account_type": "blah",
                "entity": "entity",
            },
        )
        assert response.status_code == 200
