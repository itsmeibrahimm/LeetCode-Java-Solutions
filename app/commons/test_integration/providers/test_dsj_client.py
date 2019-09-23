import aiohttp
import pytest
from app.commons.providers.dsj_client import DSJClient


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.dsj,
    pytest.mark.parametrize(
        "mode",
        [
            # the `integration` tests are integration tests against the mock obj
            pytest.param("integration", marks=[pytest.mark.integration]),
            # the `external` tests are integration tests against the real DSJ
            pytest.param("external", marks=[pytest.mark.external]),
        ],
    ),
]


# TODO: to configs... and create a new test acct for PS
TEST_DSJ_CLIENT_CONFIG = {
    "base_url": "https://api.doordash.com",
    "email": "doordash.mobile@gmail.com",
    "password": "ddmobiledriver123!",
    "jwt_token_ttl": 100,
}


class TestDSJClient:
    @pytest.fixture
    async def dsj(self, request, event_loop):
        # allow external tests to directly call external service
        if "external" in request.keywords:
            ...
        # allow integration tests to call the service mock
        elif "integration" in request.keywords:
            ...
        session = aiohttp.ClientSession(loop=event_loop)
        yield DSJClient(session=session, client_config=TEST_DSJ_CLIENT_CONFIG)
        await session.close()

    async def test__fetch_request_token(self, mode: str, dsj: DSJClient):
        token = await dsj._fetch_request_token()
        assert token is not None
