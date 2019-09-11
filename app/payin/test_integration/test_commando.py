import uuid

from requests.models import Response

from app.commons.operational_flags import COMMANDO_MODE_BOOLEAN
from starlette.testclient import TestClient

from app.conftest import RuntimeSetter
from app.payin.core.exceptions import payin_error_message_maps


class TestCommando:
    def test_commando_disables_unsupported_endpoints(
        self, runtime_setter: RuntimeSetter, client: TestClient
    ):
        runtime_setter.set(COMMANDO_MODE_BOOLEAN, True)
        stripe_dispute_id = 1
        # router dependency
        url = f"payin/api/v0/disputes/{stripe_dispute_id}/submit"

        response: Response = client.post(url, json={})
        json_resp = response.json()
        assert json_resp["error_code"] == "payin_800"
        assert json_resp["error_message"] == payin_error_message_maps["payin_800"]
        assert json_resp["retryable"] is False

        cart_payment_id = uuid.uuid4()
        # endpoint specific dependency
        url = f"/payin/api/v1/cart_payments/{cart_payment_id}/adjust"

        response = client.post(url, json={})
        json_resp = response.json()
        assert json_resp["error_code"] == "payin_800"
        assert json_resp["error_message"] == payin_error_message_maps["payin_800"]
        assert json_resp["retryable"] is False

        runtime_setter.set(COMMANDO_MODE_BOOLEAN, False)

        # router dependency
        url = f"payin/api/v0/disputes/{stripe_dispute_id}/submit"
        response = client.post(url, json={})

        json_resp = response.json()
        assert json_resp["error_code"] == "payin_100"
        assert json_resp["error_message"] == payin_error_message_maps["payin_100"]
        assert json_resp["retryable"] is False
