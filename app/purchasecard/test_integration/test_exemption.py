from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from starlette.testclient import TestClient

from app.purchasecard.api.exemption.v0.models import CreateExemptionRequest


class TestExemption:
    def test_create_exemption(self, client: TestClient):
        request_body = CreateExemptionRequest(
            creator_id="2",
            delivery_id="123",
            swipe_amount=200,
            dasher_id="123",
            mid="test_mid",
            declined_amount=100,
        )
        response = client.post(
            "/purchasecard/api/v0/marqeta/exemption", json=request_body.dict()
        )
        assert response.status_code == HTTP_201_CREATED

        request_body = CreateExemptionRequest(
            creator_id="2",
            delivery_id="wrong_delivery_id",
            swipe_amount=200,
            dasher_id="123",
            mid="test_mid",
            declined_amount=100,
        )
        response = client.post(
            "/purchasecard/api/v0/marqeta/exemption", json=request_body.dict()
        )
        assert response.status_code == HTTP_400_BAD_REQUEST
