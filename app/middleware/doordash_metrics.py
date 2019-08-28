import time
import platform

from typing import Any, Dict, Optional

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer, doorstats_global
from starlette.exceptions import ExceptionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.exceptions import ExceptionMiddleware

from app.commons.context.req_context import get_context_from_req
from app.commons.config.app_config import StatsDConfig
from app.commons.routing import reset_breadcrumbs


NORMALIZATION_TABLE = str.maketrans("/", "|", "{}")


def normalize_path(path: str):
    return path.translate(NORMALIZATION_TABLE)


def init_statsd(
    prefix: str,
    *,
    proxy: DoorStatsProxyMultiServer = None,
    host: str,
    fixed_tags: Optional[Dict[str, str]] = None,
):
    """
    Initialize a StatsD client
    """
    proxy = proxy or DoorStatsProxyMultiServer()
    proxy.initialize(host=host, prefix=prefix, fixed_tags=fixed_tags)
    return proxy


def init_statsd_from_config(
    config: StatsDConfig,
    *,
    proxy: DoorStatsProxyMultiServer = None,
    tags: Optional[Dict[str, str]] = None,
    additional_tags: Optional[Dict[str, str]] = None,
):
    combined_tags = tags or dict(**config.TAGS)
    if additional_tags:
        combined_tags.update(additional_tags)
    return init_statsd(
        config.PREFIX, proxy=proxy, host=config.SERVER, fixed_tags=combined_tags
    )


def init_global_statsd(prefix: str, *, host: str, fixed_tags: Dict[str, Any] = {}):
    fixed_tags = {"hostname": platform.node(), **fixed_tags}
    return init_statsd(prefix, proxy=doorstats_global, host=host, fixed_tags=fixed_tags)


class DoorDashMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API request level metrics for Superfund.
    These metrics are common across all DoorDash Services.
    """

    def __init__(self, app: ExceptionMiddleware, config: StatsDConfig):
        self.app = app
        self.statsd_client = init_statsd_from_config(
            config, additional_tags={"hostname": platform.node()}
        )

    async def dispatch_func(
        self: Any, request: Request, call_next: RequestResponseEndpoint
    ):
        breadcrumbs = reset_breadcrumbs(request._scope)

        context = get_context_from_req(request)

        method = request.method
        start_time = time.time()

        # get the response; the overridden routers
        # will append to the list of breadcrumbs
        response = await call_next(request)

        endpoint = normalize_path("".join(breadcrumbs))
        latency_ms = (time.time() - start_time) * 1000
        status_type = f"{response.status_code // 100}XX"
        # from the ASGI spec
        # https://github.com/django/asgiref/blob/master/specs/www.rst#L56
        path = request._scope.get("path", "")

        context.log.info(
            "request complete",
            path=path,
            endpoint=endpoint,
            method=method,
            status_code=str(response.status_code),
            latency=round(latency_ms, 3),
        )

        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(response.status_code),
        }

        self.statsd_client.incr(status_type, 1, tags=tags)
        self.statsd_client.timing("latency", latency_ms, tags=tags)

        return response
