from pytest_mock import MockFixture
from unittest.mock import Mock

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.testclient import TestClient
from fastapi.applications import FastAPI
from app.commons.routing import APIRouter
from typing import List
from app.commons.utils.testing import Stat
from app.commons.config.app_config import StatsDConfig
from app.middleware.doordash_metrics import (
    DoorDashMetricsMiddleware,
    ServiceMetricsMiddleware,
    normalize_path,
)


def test_normalize_path():
    assert normalize_path("/api/v1/{id}") == "|api|v1|id"


class MockReqContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, *, context):
        super().__init__(app)
        self.context = context

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        request.state.context = self.context
        return await call_next(request)


class TestDoorDashMetricsMiddleware:
    def test_request_path_logging(self, mocker: MockFixture):
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        router = APIRouter()

        @router.get("/level1")
        async def get_level1():
            return {"hello": "world"}

        nested_router = APIRouter()

        @nested_router.get("/level2")
        async def get_level2():
            return {"hello": "kitty"}

        sub_app = FastAPI()

        @sub_app.get("/level1")
        def get_subapp_level1():
            return {"goodbye": "moon"}

        # stich together apps
        router.include_router(nested_router, prefix="/nested")
        app.include_router(router, prefix="/nesting")
        app.mount("/subapp", sub_app)

        config = StatsDConfig()
        context: Mock = mocker.Mock()
        app.add_middleware(DoorDashMetricsMiddleware, host="localhost", config=config)
        app.add_middleware(MockReqContextMiddleware, context=context)

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            assert context.log.info.called
            args, kwargs = context.log.info.call_args
            assert args == ("request complete",)
            assert (
                kwargs["path"] == "/health"
            ), "complete path is logged for routes on app"

            context.reset_mock()

            response = client.get("/nesting/level1")
            assert response.status_code == 200
            assert response.json() == {"hello": "world"}
            assert context.log.info.called
            args, kwargs = context.log.info.call_args
            assert args == ("request complete",)
            assert (
                kwargs["path"] == "/nesting/level1"
            ), "complete path is logged for 1-level nested routes"

            context.reset_mock()

            response = client.get("/nesting/nested/level2")
            assert response.status_code == 200
            assert response.json() == {"hello": "kitty"}
            assert context.log.info.called
            args, kwargs = context.log.info.call_args
            assert args == ("request complete",)
            assert (
                kwargs["path"] == "/nesting/nested/level2"
            ), "complete path is logged for deeply nested routes"

            context.reset_mock()

            response = client.get("/subapp/level1")
            assert response.status_code == 200
            assert response.json() == {"goodbye": "moon"}
            assert context.log.info.called
            args, kwargs = context.log.info.call_args
            assert args == ("request complete",)
            assert (
                kwargs["path"] == "/subapp/level1"
            ), "complete path is logged for subapp nested routes"


class TestServiceMetricsMiddleware:
    def test_middleware(self, get_mock_statsd_events, mocker: MockFixture):
        app = mocker.Mock()  # typing: disable
        config = StatsDConfig()
        middleware = ServiceMetricsMiddleware(
            app=app, application_name="this-app-v1", host="localhost", config=config
        )
        middleware.statsd_client.incr("test.stat")

        events: List[Stat] = get_mock_statsd_events()
        assert len(events) == 1
        event = events[0]
        assert event.stat_name == "dd.pay.payment-service.test.stat"

        tags = event.tags.copy()
        container = tags.pop("container", None)
        assert container is not None, "container hostname is set"
        assert tags == {}, "no additional tags are present"

    def test_additional_tags(self, get_mock_statsd_events, mocker: MockFixture):
        app = mocker.Mock()  # typing: disable
        config = StatsDConfig()
        middleware = ServiceMetricsMiddleware(
            app=app,
            application_name="this-app-v1",
            host="localhost",
            config=config,
            additional_tags={"my": "tag"},
        )
        middleware.statsd_client.incr("test.stat")

        events: List[Stat] = get_mock_statsd_events()
        assert len(events) == 1
        event = events[0]
        assert event.stat_name == "dd.pay.payment-service.test.stat"

        tags = event.tags.copy()
        container = tags.pop("container", None)
        assert container is not None, "container hostname is set"
        assert tags == {"my": "tag"}, "additional tags are configured"
