from starlette.testclient import TestClient


class TestTransfer:
    def test_invalid(self, client: TestClient):
        response = client.get("/payout/api/v0/transfer/")
        assert response.status_code == 405, "accessing accounts requires an id"

        response = client.get("/payout/api/v0/transfer/pgp/stripe/")
        assert response.status_code == 405, "accessing accounts requires an id"

    def test_create_transfer(self, client: TestClient):
        response = client.post(
            "/payout/api/v0/transfer/",
            json={
                "subtotal": 123,
                "adjustments": "some-adjustment",
                "amount": 123,
                "method": "stripe",
            },
        )
        assert response.status_code == 200

    def test_create_stripe_transfer(self, client: TestClient):
        # first create transfer
        response = client.post(
            "/payout/api/v0/transfer/",
            json={
                "subtotal": 123,
                "adjustments": "some-adjustment",
                "amount": 123,
                "method": "stripe",
            },
        )
        transfer_id = response.json()["id"]

        response = client.post(
            "/payout/api/v0/transfer/pgp/stripe/",
            json={"stripe_status": "status", "transfer_id": transfer_id},
        )
        assert response.status_code == 200
