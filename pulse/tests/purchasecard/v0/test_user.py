import uuid

from purchasecard_v0_client import CreateMarqetaUserRequest

from tests.purchasecard.v0 import user_client


class TestUser:
    TEST_TOKEN: str = str(uuid.uuid1())
    TEST_FIRST_NAME: str = "test_first_name"
    TEST_LAST_NAME: str = "test_last_name"
    TEST_EMAIL: str = "test-marqeta4@doordash.com"

    base_create_user_request = CreateMarqetaUserRequest(
        token=TEST_TOKEN,
        first_name=TEST_FIRST_NAME,
        last_name=TEST_LAST_NAME,
        email=TEST_EMAIL,
    )

    def test_create_user(self):
        response = user_client.create_marqeta_user(self.base_create_user_request)
        assert response.token == self.TEST_TOKEN
