from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from starlette.testclient import TestClient

from app.purchasecard.api.store_metadata.v0.models import LinkStoreWithMidRequest


class TestStoreMetadata:
    def test_link_store_with_mid(self, client: TestClient):
        request_body = LinkStoreWithMidRequest(
            store_id="123", mid="123", mname="test_mname"
        )
        response = client.post(
            "/purchasecard/api/v0/marqeta/store_metadata", json=request_body.dict()
        )
        assert response.status_code == HTTP_200_OK
        parsed_response = response.json()
        assert parsed_response["updated_at"]

        request_body = LinkStoreWithMidRequest(
            store_id="wrong_store_id", mid="123", mname="test_mname"
        )
        response = client.post(
            "/purchasecard/api/v0/marqeta/store_metadata", json=request_body.dict()
        )
        assert response.status_code == HTTP_400_BAD_REQUEST
