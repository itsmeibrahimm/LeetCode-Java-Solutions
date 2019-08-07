import pytest
from starlette.testclient import TestClient
import uuid


@pytest.mark.skip("App context error - see comments in conftest")
class TestCartPayment:
    def generate_create_request_body(self, idempotency_key=None):
        request_body = {
            "payer_id": "82e8563c-8220-462f-a84d-9f8b6dd8171d",
            "amount": 500,
            "country": "US",
            "currency": "USD",
            "payment_method_id": "pm_card_visa",
            "capture_method": "manual",
            "metadata": {
                "reference_id": 123,
                "ct_reference_id": 5,
                "type": "OrderCart",
            },
        }

        if not idempotency_key:
            request_body["idempotency_key"] = str(uuid.uuid4())

        return request_body

    def test_invalid_creation(self, client: TestClient):
        request_body = self.generate_create_request_body()
        del request_body["payer_id"]
        response = client.post("/payin/api/v1/cart_payments", json=request_body)
        assert response.status_code == 422

    def test_valid_creation(self, stripe_api, client: TestClient):
        stripe_api.enable_mock()
        # stripe_api.enable_outbound()

        # TODO set up payer, payment method
        request_body = self.generate_create_request_body()
        response = client.post("/payin/api/v1/cart_payments", json=request_body)
        assert response.status_code == 201
