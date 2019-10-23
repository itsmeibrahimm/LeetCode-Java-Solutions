import pytest
from asynctest import MagicMock
import app.purchasecard.marqeta_external.error as marqeta_error

from app.purchasecard.core.user.processor import UserProcessor
from app.purchasecard.marqeta_external.models import MarqetaProviderCreateUserResponse


class FunctionMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(FunctionMock, self).__call__(*args, **kwargs)


class TestUserProcessor:
    pytestmark = [pytest.mark.asyncio]
    TEST_TOKEN: str = "user_processor_test_token"

    @pytest.fixture
    def fake_marqeta_client(self):
        mock_marqeta_client = MagicMock()
        mock_marqeta_client.create_marqeta_user = FunctionMock()
        mock_marqeta_client.create_marqeta_user.return_value = MarqetaProviderCreateUserResponse(
            token=self.TEST_TOKEN
        )
        return mock_marqeta_client

    async def test_create_user(self, fake_marqeta_client):
        fake_marqeta_client.create_marqeta_user.return_value = MarqetaProviderCreateUserResponse(
            token=self.TEST_TOKEN
        )

        user_processor = UserProcessor(
            marqeta_client=fake_marqeta_client, logger=MagicMock()
        )
        result_create_user = await user_processor.create_marqeta_user(
            token=self.TEST_TOKEN,
            first_name="jasmine",
            last_name="tea",
            email="jasmine-tea@doordash.com",
        )
        assert result_create_user
        assert result_create_user.token == self.TEST_TOKEN

    async def test_create_user_dup_email(self, fake_marqeta_client):
        fake_marqeta_client.create_marqeta_user.side_effect = [
            marqeta_error.DuplicateEmail,
            MarqetaProviderCreateUserResponse(token=self.TEST_TOKEN),
        ]

        user_processor = UserProcessor(
            marqeta_client=fake_marqeta_client, logger=MagicMock()
        )

        result_create_user_dup_email = await user_processor.create_marqeta_user(
            token=self.TEST_TOKEN,
            first_name="jasmine",
            last_name="tea",
            email="jasmine-tea@doordash.com",
        )

        assert result_create_user_dup_email
        assert result_create_user_dup_email.token == self.TEST_TOKEN

    async def test_create_user_api_error(self, fake_marqeta_client):
        fake_marqeta_client.create_marqeta_user.side_effect = [
            marqeta_error.DuplicateEmail,
            MarqetaProviderCreateUserResponse(token=self.TEST_TOKEN),
        ]
