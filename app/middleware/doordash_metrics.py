import time
import platform

from typing import Any, Dict, Optional

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer, doorstats_global
from starlette.exceptions import ExceptionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.exceptions import ExceptionMiddleware

from app.commons.context.req_context import get_context_from_req
from app.commons.config.app_config import AppConfig
from app.commons.routing import reset_breadcrumbs


DEFAULT_HOSTNAME = "unknown-hostname"
DEFAULT_CLUSTER = "unknown-cluster"
DEFAULT_SERVICE_NAME = "unknown-service"
DEFAULT_STATSD_SERVER = "prod-proxy-internal.doordash.com"

NORMALIZATION_TABLE = str.maketrans("/", "|", "{}")


def normalize_path(path: str):
    return path.translate(NORMALIZATION_TABLE)


def init_statsd(
    prefix: str,
    *,
    proxy: DoorStatsProxyMultiServer = None,
    host: str = DEFAULT_STATSD_SERVER,
    fixed_tags: Optional[Dict[str, Any]] = None,
):
    """
    Initialize a StatsD client
    """
    proxy = proxy or DoorStatsProxyMultiServer()
    proxy.initialize(host=host, prefix=prefix, fixed_tags=fixed_tags)
    return proxy


def init_global_statsd(
    prefix: str, *, host: str = DEFAULT_STATSD_SERVER, fixed_tags: Dict[str, Any] = {}
):
    fixed_tags = {"hostname": platform.node(), **fixed_tags}
    return init_statsd(prefix, proxy=doorstats_global, fixed_tags=fixed_tags)


class DoorDashMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app: ExceptionMiddleware, config: AppConfig, stats_prefix="dd.response"
    ):
        self.app = app

        fixed_tags = {"hostname": platform.node(), **config.METRICS_CONFIG}
        self.statsd_client = init_statsd(
            stats_prefix, host=config.STATSD_SERVER, fixed_tags=fixed_tags
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
        latency = int((time.time() - start_time) * 1000)
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
            latency=latency,
        )

        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(response.status_code),
        }

        self.statsd_client.incr(status_type, 1, tags=tags)
        self.statsd_client.timing("latency", latency, tags=tags)

        return response
