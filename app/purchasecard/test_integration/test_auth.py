from uuid import uuid4

from starlette.status import HTTP_201_CREATED, HTTP_200_OK
from starlette.testclient import TestClient

from app.purchasecard.api.auth.v0.models import (
    CreateAuthRequest,
    StoreInfo,
    UpdateAuthRequest,
    CloseAuthRequest,
    CloseAllAuthRequest,
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
        delivery_id = str(uuid4())
        shift_id = str(uuid4())
        create_auth_request = CreateAuthRequest(
            subtotal=123,
            subtotal_tax=123,
            store_meta=StoreInfo(
                store_id="111",
                store_city="Mountain View",
                store_business_name="Dish Dash",
            ),
            delivery_id=delivery_id,
            delivery_requires_purchase_card=True,
            shift_id=shift_id,
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
            delivery_id=delivery_id,
            shift_id=shift_id,
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
            delivery_id=delivery_id,
            shift_id=shift_id,
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

        new_delivery_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        shift_id = str(uuid4())

        create_auth_request = CreateAuthRequest(
            subtotal=123,
            subtotal_tax=123,
            store_meta=StoreInfo(
                store_id="111",
                store_city="Mountain View",
                store_business_name="Dish Dash",
            ),
            delivery_id=new_delivery_ids[0],
            delivery_requires_purchase_card=True,
            shift_id=shift_id,
            ttl=None,
        )

        other_auth_requests = [
            CreateAuthRequest(
                subtotal=123,
                subtotal_tax=123,
                store_meta=StoreInfo(
                    store_id="111",
                    store_city="Mountain View",
                    store_business_name="Dish Dash",
                ),
                delivery_id=new_delivery_ids[1],
                delivery_requires_purchase_card=True,
                shift_id=shift_id,
                ttl=None,
            ),
            CreateAuthRequest(
                subtotal=123,
                subtotal_tax=123,
                store_meta=StoreInfo(
                    store_id="111",
                    store_city="Mountain View",
                    store_business_name="Dish Dash",
                ),
                delivery_id=new_delivery_ids[2],
                delivery_requires_purchase_card=True,
                shift_id=shift_id,
                ttl=None,
            ),
        ]

        response = client.post(
            "purchasecard/api/v0/marqeta/auth", json=create_auth_request.dict()
        )

        client.post(
            "purchasecard/api/v0/marqeta/auth", json=other_auth_requests[0].dict()
        )
        client.post(
            "purchasecard/api/v0/marqeta/auth", json=other_auth_requests[1].dict()
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
            delivery_id=new_delivery_ids[0],
            shift_id=shift_id,
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
            delivery_id=new_delivery_ids[0],
            shift_id=shift_id,
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
            delivery_id=new_delivery_ids[0], shift_id=shift_id
        )

        response = client.post(
            "purchasecard/api/v0/marqeta/auth/close", json=close_auth_request.dict()
        )

        assert response.status_code == HTTP_200_OK
        assert response.json()["state"] == AuthRequestStateName.CLOSED_MANUAL

        close_all_request = CloseAllAuthRequest(shift_id=shift_id)

        response = client.post(
            "purchasecard/api/v0/marqeta/auth/close/all", json=close_all_request.dict()
        )
        assert response.status_code == HTTP_200_OK
        assert response.json()["num_success"] == 2
        assert response.json()["states"] == [
            AuthRequestStateName.CLOSED_MANUAL,
            AuthRequestStateName.CLOSED_MANUAL,
        ]

        close_all_request = CloseAllAuthRequest(shift_id=shift_id)

        response = client.post(
            "purchasecard/api/v0/marqeta/auth/close/all", json=close_all_request.dict()
        )
        assert response.status_code == HTTP_200_OK
        assert response.json()["num_success"] == 0
        assert response.json()["states"] == []
