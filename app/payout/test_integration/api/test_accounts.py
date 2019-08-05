from starlette.testclient import TestClient


class TestAccount:
    def test_invalid(self, client: TestClient):
        response = client.get("/payout/api/v0/account/")
        assert response.status_code == 405, "accessing accounts requires an id"

        response = client.get("/payout/api/v0/account/pgp/stripe/")
        assert response.status_code == 405, "accessing accounts requires an id"

    def test_create_payment_account(self, client: TestClient):
        response = client.post(
            "/payout/api/v0/account/",
            json={
                "statement_descriptor": "yup",
                "account_type": "blah",
                "entity": "entity",
            },
        )
        assert response.status_code == 200

    def test_create_stripe_managed_account(self, client: TestClient):
        response = client.post(
            "/payout/api/v0/account/pgp/stripe/",
            json={"stripe_id": "stripe123", "country_shortname": "us"},
        )
        assert response.status_code == 200
