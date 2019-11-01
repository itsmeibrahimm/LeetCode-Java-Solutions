import pytest
import uuid
import starlette.exceptions

from pytest_mock import MockFixture
from unittest.mock import Mock
from typing import Optional

from app.middleware.newrelic_metrics import NewRelicMetricsMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from fastapi.applications import FastAPI
from app.commons.routing import APIRouter
from starlette.testclient import TestClient
from app.commons.context.req_context import ReqContext


def test_newrelic_middleware(mocker: MockFixture):
    app = FastAPI()
    req_id = uuid.uuid4()
    correlation_id: Optional[str] = "abc_123"

    class ReqContextMiddleware(BaseHTTPMiddleware):
        def __init__(self, app):
            self.app = app

        async def dispatch_func(self, request, call_next):
            request.state.context = ReqContext(
                req_id=req_id,
                log=mocker.Mock(),
                commando_mode=False,
                correlation_id=correlation_id,
                stripe_async_client=mocker.Mock(),
                commando_legacy_payment_white_list=[],
                verify_card_in_commando_mode=False,
            )
            return await call_next(request)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/error")
    async def error():
        raise RuntimeError("unhandled error")

    @app.get("/http-error")
    async def http_error():
        raise starlette.exceptions.HTTPException(status_code=403)

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
    app.add_middleware(ReqContextMiddleware)

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
    mock_add_custom_parameter = mocker.patch("newrelic.agent.add_custom_parameter")
    mock_record_exception = mocker.patch("newrelic.agent.record_exception")

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        assert mock_web_transaction.called
        args, kwargs = mock_web_transaction.call_args
        assert kwargs["request_path"] == "/health"

        assert mock_set_transaction.called
        args, kwargs = mock_set_transaction.call_args
        assert args[0] == "app.middleware.test_unit.test_newrelic_metrics.health"

        assert mock_add_custom_parameter.call_count == 2
        assert mock_add_custom_parameter.called_with("req_id", str(req_id))
        assert mock_add_custom_parameter.called_with("correlation_id", "abc_123")

        mock_web_transaction.reset_mock()
        mock_set_transaction.reset_mock()
        mock_add_custom_parameter.reset_mock()
        mock_record_exception.reset_mock()

        # nested router
        correlation_id = None
        response = client.get("/nesting/nested/level2")
        assert response.status_code == 200

        assert mock_web_transaction.called
        args, kwargs = mock_web_transaction.call_args
        assert kwargs["request_path"] == "/nesting/nested/level2"

        assert mock_set_transaction.called
        args, kwargs = mock_set_transaction.call_args
        assert args[0] == "app.middleware.test_unit.test_newrelic_metrics.get_level2"

        assert mock_add_custom_parameter.call_count == 1
        assert mock_add_custom_parameter.called_with("req_id", str(req_id))

        mock_web_transaction.reset_mock()
        mock_set_transaction.reset_mock()
        mock_add_custom_parameter.reset_mock()
        mock_record_exception.reset_mock()

        # exception handling
        with pytest.raises(RuntimeError):
            # NOTE: unhandled exceptions are not caught using test client
            response = client.get("/error")

        assert mock_record_exception.called
        assert mock_record_exception.called_with(
            RuntimeError("unhandled_error")
        ), "unhandled exceptions are passed to newrelic"

        mock_web_transaction.reset_mock()
        mock_set_transaction.reset_mock()
        mock_add_custom_parameter.reset_mock()
        mock_record_exception.reset_mock()

        response = client.get("/http-error")
        assert response.status_code == 403
        assert (
            not mock_record_exception.called
        ), "exception is not recorded for handled errors"
