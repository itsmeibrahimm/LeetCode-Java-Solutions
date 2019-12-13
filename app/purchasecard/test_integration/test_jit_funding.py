from starlette.status import HTTP_200_OK
from starlette.testclient import TestClient

from app.purchasecard.api.jit_funding.v0.models import (
    MarqetaJITFundingRequest,
    LinkStoreWithMidRequest,
)


class TestMarqetaJITFunding:
    """

    """

    def test_jit_funding_route(self, client: TestClient):
        request_body = MarqetaJITFundingRequest()
        response = client.post(
            "/purchasecard/api/v0/marqeta/jit_funding", json=request_body.dict()
        )

        assert response.status_code == HTTP_200_OK

    def test_link_store_with_mid(self, client: TestClient):
        request_body = LinkStoreWithMidRequest(
            store_id="123", mid="123", mname="test_mname"
        )
        response = client.post(
            "/purchasecard/api/v0/marqeta/jit_funding/store_metadata",
            json=request_body.dict(),
        )
        assert response.status_code == HTTP_200_OK
        parsed_response = response.json()
        assert parsed_response["updated_at"]
