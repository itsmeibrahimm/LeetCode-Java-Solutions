from starlette.testclient import TestClient
import json
import pytest

from app.commons.providers.dsj_client import DSJClient


class TestWebhook:
    @pytest.fixture
    def dsj_client(self, mocker) -> DSJClient:
        # return DSJClient(
        #     {
        #         "base_url": app_config.DSJ_API_BASE_URL,
        #         "email": app_config.DSJ_API_USER_EMAIL.value,
        #         "password": app_config.DSJ_API_USER_PASSWORD.value,
        #         "jwt_token_ttl": app_config.DSJ_API_JWT_TOKEN_TTL,
        #     }
        # )

        # mock out DSJ for now until we can run real integration test with test data
        mock_dsj = mocker.patch("app.commons.providers.dsj_client.DSJClient")
        mock_dsj.post.return_value = None
        return mock_dsj

    def test_invalid(self, client: TestClient, dsj_client: DSJClient):
        response = client.post(
            "/payout/api/v0/webhook/us",
            json={
                "created": 1326853478,
                "id": "evt_00000000000000",
                "type": "not recognizable",
                "object": "event",
                "api_version": "2019-05-16",
                "data": {"object": {"id": "tr_00000000000000", "status": "pending"}},
            },
        )
        assert response.status_code == 400
        assert json.loads(response.content) == {"detail": "Error"}

    def test_transfer_event(self, client: TestClient, dsj_client: DSJClient):
        response = client.post(
            "/payout/api/v0/webhook/us",
            json={
                "created": 1326853478,
                "id": "evt_00000000000000",
                "type": "transfer.created",
                "object": "event",
                "api_version": "2019-05-16",
                "data": {
                    "object": {
                        "id": "tr_00000000000000",
                        "status": "pending",
                        "method": "instant",
                    }
                },
            },
        )
        assert response.status_code == 200
