import asyncio

import aiohttp
import pytest

from aiohttp import web
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_200_OK, HTTP_306_RESERVED

from app.commons.providers.identity_client import (
    IdentityClient,
    ClientTimeoutError,
    UnauthorizedError,
    ClientReponseError,
    InternalIdentityBaseError,
)
from app.commons.providers.identity_models import VerifyTokenResponse


class TestIdentityClient:
    pytestmark = [pytest.mark.asyncio]
    service_id: int = 123
    route = f"/api/v1/verify/{str(service_id)}"

    async def _make_ids_client(
        self, ids_app: aiohttp.web.Application, aiohttp_client, timeout: int = 3
    ):
        client: aiohttp.test_utils.TestClient = await aiohttp_client(ids_app)
        identity_client = IdentityClient(
            http_endpoint=f"http://{client.host}:{client.port}",
            grpc_endpoint="Nah nah nah Zohaib",
            session=client.session,
            default_timeout=timeout,
        )
        return identity_client

    @pytest.fixture
    async def timeout_ids_client(self, aiohttp_client):
        sleep_time = 2

        async def auth(request):
            response = VerifyTokenResponse(
                client_id=321,
                client_name="Heero Yuy",
                service_id=123,
                service_name="Wing Gundam",
            )
            await asyncio.sleep(sleep_time)
            return web.json_response(response.dict())

        ids_app = web.Application()

        ids_app.router.add_get(self.route, auth)
        return await self._make_ids_client(
            ids_app, aiohttp_client, timeout=sleep_time + 2
        )

    @pytest.fixture
    async def unauth_ids_client(self, aiohttp_client):
        async def auth(request):
            return web.Response(
                status=HTTP_401_UNAUTHORIZED, reason="Because Zohaib is not being nice"
            )

        ids_app = web.Application()
        ids_app.router.add_get(self.route, auth)
        return await self._make_ids_client(ids_app, aiohttp_client)

    @pytest.fixture
    async def bad_response_ids_client(self, aiohttp_client):
        async def auth(request):
            return web.Response(status=HTTP_200_OK, text="This shouldn't be here")

        ids_app = web.Application()
        ids_app.router.add_get(self.route, auth)
        return await self._make_ids_client(ids_app, aiohttp_client)

    @pytest.fixture
    async def bad_status_ids_client(self, aiohttp_client):
        async def auth(request):
            return web.Response(status=HTTP_306_RESERVED)

        ids_app = web.Application()
        ids_app.router.add_get(self.route, auth)
        return await self._make_ids_client(ids_app, aiohttp_client)

    @pytest.fixture
    def loop(self, event_loop):
        """
        override the loop fixture provided by aiohttp test_utils
        :param event_loop:
        :return:
        """
        yield event_loop

    async def test_timeout(self, timeout_ids_client: IdentityClient):

        with pytest.raises(ClientTimeoutError):
            await timeout_ids_client.verify_api_key_with_http(
                self.service_id, "OZ", "Treize Khushrenada", timeout=1
            )

        # this should use the default timeout which is less than the sleep time in timeout_ids_application
        await timeout_ids_client.verify_api_key_with_http(
            123, "OZ", "Treize Khushrenada"
        )

    async def test_unauth(self, unauth_ids_client: IdentityClient):
        with pytest.raises(UnauthorizedError):
            await unauth_ids_client.verify_api_key_with_http(
                self.service_id, "OZ", "Treize Khushrenada", timeout=1
            )

    async def test_bad_ids_response(self, bad_response_ids_client: IdentityClient):
        with pytest.raises(ClientReponseError):
            await bad_response_ids_client.verify_api_key_with_http(
                self.service_id, "OZ", "Treize Khushrenada", timeout=1
            )

    async def test_bad_ids_status(self, bad_status_ids_client: IdentityClient):
        with pytest.raises(InternalIdentityBaseError):
            await bad_status_ids_client.verify_api_key_with_http(
                self.service_id, "OZ", "Treize Khushrenada", timeout=1
            )
