from starlette.testclient import TestClient
import json


class TestWebhook:
    def test_invalid(self, client: TestClient):
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

    def test_transfer_event(self, client: TestClient):
        response = client.post(
            "/payout/api/v0/webhook/us",
            json={
                "created": 1326853478,
                "id": "evt_00000000000000",
                "type": "transfer.created",
                "object": "event",
                "api_version": "2019-05-16",
                "data": {"object": {"id": "tr_00000000000000", "status": "pending"}},
            },
        )
        assert response.status_code == 200
        assert json.loads(response.content) == {
            "country_code": "us",
            "id": "evt_00000000000000",
            "stripe_id": "tr_00000000000000",
        }
