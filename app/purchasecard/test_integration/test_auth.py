from uuid import uuid4

from starlette.status import HTTP_201_CREATED
from starlette.testclient import TestClient

from app.purchasecard.api.auth.v0.models import CreateAuthRequest, StoreInfo


class TestAuth:
    def test_create_auth(self, client: TestClient):
        request_body = CreateAuthRequest(
            subtotal=123,
            subtotal_tax=123,
            store_meta=StoreInfo(
                store_id="test_store_id",
                store_city="test_store_city",
                store_business_name="test_business_name",
            ),
            delivery_id=str(uuid4()),
            delivery_requires_purchase_card=True,
            shift_id="test_shift_id",
            ttl=None,
        )

        response = client.post(
            "purchasecard/api/v0/marqeta/auth", json=request_body.dict()
        )

        assert response.status_code == HTTP_201_CREATED
