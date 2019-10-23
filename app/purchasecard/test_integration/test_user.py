from typing import Dict, Any

import pytest
from starlette.status import HTTP_201_CREATED
from starlette.testclient import TestClient


@pytest.mark.external
class TestCreateMarqetaUser:
    TEST_TOKEN: str = "user_processor_test_token"

    def _get_create_marqeta_user_request(
        self, token: str, first_name: str, last_name: str, email: str
    ) -> Dict[str, Any]:
        request_body = {
            "token": token,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        }
        return request_body

    @pytest.mark.skip
    def test_create_user(self, client: TestClient):
        request_body = self._get_create_marqeta_user_request(
            token=self.TEST_TOKEN,
            first_name="jasmine",
            last_name="tea",
            email="jasmine-tea@doordash.com",
        )
        response = client.post(
            "/purchasecard/api/v0/user/create_marqeta", json=request_body
        )

        assert response.status_code == HTTP_201_CREATED

        user = response.json()
        assert user
        assert user["token"] == self.TEST_TOKEN
