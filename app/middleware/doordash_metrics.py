import platform
import time
from typing import Any, Dict, Optional

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer
from starlette.exceptions import ExceptionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import Scope

from app.commons import tracing
from app.commons.config.app_config import StatsDConfig
from app.commons.context.req_context import get_context_from_req
from app.commons.routing import reset_breadcrumbs, get_endpoint_breadcrumbs
from app.commons.stats import (
    create_statsd_client_from_config,
    set_service_stats_client,
    set_request_logger,
)

NORMALIZATION_TABLE = str.maketrans("/", "|", "{}")


def normalize_path(path: str):
    return path.translate(NORMALIZATION_TABLE)


def get_endpoint_from_scope(scope: Scope) -> str:
    bread_crumbs = get_endpoint_breadcrumbs(scope)
    return normalize_path("".join(bread_crumbs)) if bread_crumbs else ""


class DoorDashMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API request level metrics for Superfund.
    These metrics are common across all DoorDash Services.
    """

    def __init__(self, app: ExceptionMiddleware, *, host: str, config: StatsDConfig):
        self.app = app
        self.statsd_client = create_statsd_client_from_config(
            host, config, additional_tags={"hostname": platform.node()}
        )
        config2 = StatsDConfig(PREFIX="dd.pay.payment-service", TAGS=config.TAGS)
        self.statsd_client2 = create_statsd_client_from_config(
            host, config2, additional_tags={"hostname": platform.node()}
        )

    async def dispatch_func(
        self: Any, request: Request, call_next: RequestResponseEndpoint
    ):
        reset_breadcrumbs(request.scope)

        context = get_context_from_req(request)

        method = request.method
        start_time = time.perf_counter()

        # from the ASGI spec
        # https://github.com/django/asgiref/blob/master/specs/www.rst#L56

        # fetch the path BEFORE we pass it to the app
        # the leading path components get stripped off
        # as routing traverses sub-apps
        path = request.scope.get("path", "")
        user_agent = request.headers.get("User-Agent", "")

        # make the request logger available to
        # app-level resources
        with set_request_logger(context.log):
            # get the response; the overridden routers
            # will append to the list of breadcrumbs
            response = await call_next(request)

        # breadcrumbs are available after
        endpoint = get_endpoint_from_scope(request.scope)

        # latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        status_type = f"{response.status_code // 100}XX"

        # size
        try:
            size = int(response.headers.get("Content-Length", "0"))
        except ValueError:
            size = 0

        context.log.info(
            "request complete",
            path=path,
            endpoint=endpoint,
            method=method,
            status_code=str(response.status_code),
            latency=round(latency_ms, 3),
            user_agent=user_agent,
            size=size,
        )

        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(response.status_code),
        }

        self.statsd_client.incr(status_type, 1, tags=tags)
        self.statsd_client.timing("latency", latency_ms, tags=tags)
        self.statsd_client2.timing("response.latency", latency_ms, tags=tags)

        return response


class ServiceMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to Service level metrics for Superfund
    """

    statsd_client: DoorStatsProxyMultiServer

    def __init__(
        self,
        app: ExceptionMiddleware,
        *,
        application_name: str,
        host: str,
        config: StatsDConfig,
        additional_tags: Optional[Dict[str, str]] = None,
    ):
        self.app = app
        self.application_name = application_name

        combined_tags = {"container": platform.node()}
        if additional_tags:
            combined_tags.update(additional_tags)

        self.statsd_client = create_statsd_client_from_config(
            host, config, additional_tags=combined_tags
        )

    async def dispatch_func(
        self: Any, request: Request, call_next: RequestResponseEndpoint
    ):
        # use the service's client instead of the global statsd client
        with set_service_stats_client(
            self.statsd_client
        ), tracing.breadcrumb_ctxt_manager(
            tracing.Breadcrumb(application_name=self.application_name)
        ):
            response = await call_next(request)
        return response
