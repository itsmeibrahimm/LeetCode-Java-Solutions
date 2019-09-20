import pytest
import asyncio
from contextvars import copy_context
import stripe.error

from typing import List
from app.commons import tracing
from app.commons.utils.testing import Stat
from app.commons.providers.stripe import stripe_http_client

from aiohttp import web
from aiohttp.test_utils import TestServer as AioHTTPTestServer


@pytest.fixture(autouse=True)
def setup(service_statsd_client):
    # ensure that we mock the statsd service client
    ...


class TestStripeHttpClient:
    def get_application(self):
        async def ok(request):
            return web.Response()

        async def internal_error(request):
            raise web.HTTPInternalServerError()

        app = web.Application()
        app.router.add_get("/", ok)
        app.router.add_get("/error", internal_error)
        return app

    @pytest.fixture
    async def server_port(
        self, unused_tcp_port: int, event_loop: asyncio.AbstractEventLoop
    ):
        server = AioHTTPTestServer(self.get_application(), port=unused_tcp_port)
        await server.start_server(event_loop)
        yield unused_tcp_port
        await server.close()

    @pytest.mark.asyncio
    async def test_exception(self, get_mock_statsd_events, unused_tcp_port: int):
        client = stripe_http_client.TimedRequestsClient()
        url = f"http://localhost:{unused_tcp_port}"
        with pytest.raises(stripe.error.StripeError), tracing.breadcrumb_as(
            tracing.Breadcrumb(application_name="myapp", country="US")
        ):
            client.request("GET", url, {})

        events: List[Stat] = get_mock_statsd_events()
        assert len(events) == 1
        event = events[0]
        assert event.stat_name == "dd.pay.payment-service.io.stripe-lib.latency"
        assert event.tags == {
            "application_name": "myapp",
            "country": "US",
            "request_status": "exception",
        }, "cannot connect to server"

    @pytest.mark.asyncio
    async def test_response(
        self,
        get_mock_statsd_events,
        reset_mock_statsd_events,
        server_port: int,
        event_loop: asyncio.AbstractEventLoop,
    ):
        client = stripe_http_client.TimedRequestsClient()
        port = server_port

        with tracing.breadcrumb_as(
            tracing.Breadcrumb(application_name="app2", country="AU")
        ):
            url = f"http://localhost:{port}/"
            context = copy_context()
            await event_loop.run_in_executor(
                None, context.run, client.request, "GET", url, {}
            )

        events: List[Stat] = get_mock_statsd_events()
        assert len(events) == 1
        event = events[0]
        assert event.stat_name == "dd.pay.payment-service.io.stripe-lib.latency"
        assert event.tags == {
            "application_name": "app2",
            "country": "AU",
            "request_status": "success",
            "status_code": "200",
        }, "successful response"

        reset_mock_statsd_events()

        with tracing.breadcrumb_as(
            tracing.Breadcrumb(application_name="myapp", country="CA")
        ):
            url = f"http://localhost:{port}/error"
            context = copy_context()
            await event_loop.run_in_executor(
                None, context.run, client.request, "GET", url, {}
            )

        events = get_mock_statsd_events()
        assert len(events) == 1
        event = events[0]
        assert event.stat_name == "dd.pay.payment-service.io.stripe-lib.latency"
        assert event.tags == {
            "application_name": "myapp",
            "country": "CA",
            "request_status": "server_error",
            "status_code": "500",
        }, "cannot connect to server"
