from uuid import uuid4

from starlette.status import HTTP_201_CREATED, HTTP_200_OK
from starlette.testclient import TestClient

from app.purchasecard.api.auth.v0.models import (
    CreateAuthRequest,
    StoreInfo,
    UpdateAuthRequest,
    CloseAuthRequest,
)
from app.purchasecard.models.paymentdb.auth_request_state import AuthRequestStateName


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

    def test_update_auth(self, client: TestClient):
        delivery_str_id = str(uuid4())

        create_auth_request = CreateAuthRequest(
            subtotal=123,
            subtotal_tax=123,
            store_meta=StoreInfo(
                store_id="111",
                store_city="Mountain View",
                store_business_name="Dish Dash",
            ),
            delivery_id=delivery_str_id,
            delivery_requires_purchase_card=True,
            shift_id="222",
            ttl=None,
        )

        response = client.post(
            "purchasecard/api/v0/marqeta/auth", json=create_auth_request.dict()
        )

        assert response.status_code == HTTP_201_CREATED

        update_auth_first_request = UpdateAuthRequest(
            subtotal=10,
            subtotal_tax=2,
            store_meta=StoreInfo(
                store_id="111",
                store_city="Mountain View",
                store_business_name="Dish Dash",
            ),
            delivery_id=delivery_str_id,
            shift_id="222",
            delivery_requires_purchase_card=True,
        )

        response = client.post(
            "purchasecard/api/v0/marqeta/auth/update",
            json=update_auth_first_request.dict(),
        )

        assert response.status_code == HTTP_200_OK
        assert response.json()["state"] == AuthRequestStateName.ACTIVE_UPDATED
        old_updated_at = response.json()["updated_at"]

        update_auth_second_request = UpdateAuthRequest(
            subtotal=10,
            subtotal_tax=2,
            store_meta=StoreInfo(
                store_id="111",
                store_city="Mountain View",
                store_business_name="Dish Dash",
            ),
            delivery_id=delivery_str_id,
            shift_id="222",
            delivery_requires_purchase_card=True,
            ttl=20,
        )

        response = client.post(
            "purchasecard/api/v0/marqeta/auth/update",
            json=update_auth_second_request.dict(),
        )

        assert response.status_code == HTTP_200_OK
        assert response.json()["updated_at"] > old_updated_at

    def test_auth_flow(self, client: TestClient):
        delivery_str_id = str(uuid4())

        create_auth_request = CreateAuthRequest(
            subtotal=123,
            subtotal_tax=123,
            store_meta=StoreInfo(
                store_id="111",
                store_city="Mountain View",
                store_business_name="Dish Dash",
            ),
            delivery_id=delivery_str_id,
            delivery_requires_purchase_card=True,
            shift_id="222",
            ttl=None,
        )

        response = client.post(
            "purchasecard/api/v0/marqeta/auth", json=create_auth_request.dict()
        )

        assert response.status_code == HTTP_201_CREATED

        update_auth_first_request = UpdateAuthRequest(
            subtotal=10,
            subtotal_tax=2,
            store_meta=StoreInfo(
                store_id="111",
                store_city="Mountain View",
                store_business_name="Dish Dash",
            ),
            delivery_id=delivery_str_id,
            shift_id="222",
            delivery_requires_purchase_card=True,
        )

        response = client.post(
            "purchasecard/api/v0/marqeta/auth/update",
            json=update_auth_first_request.dict(),
        )

        assert response.status_code == HTTP_200_OK
        assert response.json()["state"] == AuthRequestStateName.ACTIVE_UPDATED
        old_updated_at = response.json()["updated_at"]

        update_auth_second_request = UpdateAuthRequest(
            subtotal=9,
            subtotal_tax=2,
            store_meta=StoreInfo(
                store_id="111",
                store_city="Mountain View",
                store_business_name="Dish Dash",
            ),
            delivery_id=delivery_str_id,
            shift_id="222",
            delivery_requires_purchase_card=True,
            ttl=20,
        )

        response = client.post(
            "purchasecard/api/v0/marqeta/auth/update",
            json=update_auth_second_request.dict(),
        )

        assert response.status_code == HTTP_200_OK
        assert response.json()["updated_at"] > old_updated_at

        close_auth_request = CloseAuthRequest(
            delivery_id=delivery_str_id, shift_id="222"
        )

        response = client.post(
            "purchasecard/api/v0/marqeta/auth/close", json=close_auth_request.dict()
        )

        assert response.status_code == HTTP_200_OK
        assert response.json()["state"] == AuthRequestStateName.CLOSED_MANUAL
