from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from starlette.testclient import TestClient


class TestMarqetaTransaction:
    def test_fundable_amount_by_delivery(self, client: TestClient):
        response = client.get(
            "/purchasecard/api/v0/marqeta/transaction/fundable_amount/15?restaurant_total=0"
        )
        assert response.json()["fundable_amount"] == 0
        assert response.status_code == HTTP_200_OK

    def test_funded_amount_by_delivery(self, client: TestClient):
        response = client.get(
            "/purchasecard/api/v0/marqeta/transaction/funded_amount/15"
        )
        assert response.json()["funded_amount"] == 0
        assert response.status_code == HTTP_200_OK

    def test_has_associated_marqeta_transaction(self, client: TestClient):
        response = client.get(
            "/purchasecard/api/v0/marqeta/transaction/associated/15?ignore_timed_out=False"
        )
        assert not response.json()["has_marqeta_transaction"]
        assert response.status_code == HTTP_200_OK

        response = client.get(
            "/purchasecard/api/v0/marqeta/transaction/associated/15?ignore_timed_out=True"
        )
        assert not response.json()["has_marqeta_transaction"]
        assert response.status_code == HTTP_200_OK

        response = client.get(
            "/purchasecard/api/v0/marqeta/transaction/associated/fake_delivery_id?ignore_timed_out=False"
        )
        assert response.status_code == HTTP_400_BAD_REQUEST
