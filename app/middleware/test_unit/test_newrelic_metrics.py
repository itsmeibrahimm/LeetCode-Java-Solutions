from pytest_mock import MockFixture
from unittest.mock import Mock

from app.middleware.newrelic_metrics import NewRelicMetricsMiddleware

from fastapi.applications import FastAPI
from app.commons.routing import APIRouter
from starlette.testclient import TestClient


def test_newrelic_middleware(mocker: MockFixture):
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    router = APIRouter()
    nested_router = APIRouter()

    @nested_router.get("/level2")
    async def get_level2():
        return {"hello": "kitty"}

    # stich together apps
    router.include_router(nested_router, prefix="/nested")
    app.include_router(router, prefix="/nesting")

    # include middleware
    app.add_middleware(NewRelicMetricsMiddleware)

    mocker.patch("app.commons.instrumentation.newrelic.application_instance")
    mocker.patch(
        "app.commons.instrumentation.newrelic.current_transaction", return_value=None
    )
    mock_web_transaction: Mock = mocker.patch(
        "app.commons.instrumentation.newrelic.WebTransaction"
    )

    def check_transaction(*args, **kwargs):
        assert (
            mock_web_transaction.return_value.__enter__.called
        ), "WebTransaction contextmanager is entered"
        assert (
            not mock_web_transaction.return_value.__exit__.called
        ), "set_transaction is called inside the contextmanager"

    mock_set_transaction: Mock = mocker.patch(
        "newrelic.agent.set_transaction_name", side_effect=check_transaction
    )

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        assert mock_web_transaction.called
        args, kwargs = mock_web_transaction.call_args
        assert kwargs["request_path"] == "/health"

        assert mock_set_transaction.called
        args, kwargs = mock_set_transaction.call_args
        assert args[0] == "app.middleware.test_unit.test_newrelic_metrics.health"

        mock_web_transaction.reset_mock()
        mock_set_transaction.reset_mock()

        # nested router
        response = client.get("/nesting/nested/level2")
        assert response.status_code == 200

        assert mock_web_transaction.called
        args, kwargs = mock_web_transaction.call_args
        assert kwargs["request_path"] == "/nesting/nested/level2"

        assert mock_set_transaction.called
        args, kwargs = mock_set_transaction.call_args
        assert args[0] == "app.middleware.test_unit.test_newrelic_metrics.get_level2"
