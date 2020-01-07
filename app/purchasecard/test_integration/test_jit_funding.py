from starlette.status import HTTP_200_OK
from starlette.testclient import TestClient

from app.purchasecard.api.jit_funding.v0.models import MarqetaJITFundingRequest


class TestMarqetaJITFunding:
    """

    """

    def test_jit_funding_route(self, client: TestClient):
        request_body = MarqetaJITFundingRequest()
        response = client.post(
            "/purchasecard/api/v0/marqeta/jit_funding", json=request_body.dict()
        )

        assert response.status_code == HTTP_200_OK
