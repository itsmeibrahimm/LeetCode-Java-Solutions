import os
import time

from typing import Any

from doordash_python_stats.ddstats import doorstats_global
from starlette.exceptions import ExceptionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.routing import Match

from app.commons.context.req_context import get_context_from_req


DEFAULT_HOSTNAME = "unknown-hostname"
DEFAULT_CLUSTER = "unknown-cluster"
DEFAULT_SERVICE_NAME = "unknown-service"
DEFAULT_STATSD_SERVER = "prod-proxy-internal.doordash.com"


def init_statsd(statsd_server: str, service_name: str, cluster: str):
    hostname = os.getenv("HOSTNAME", DEFAULT_HOSTNAME)
    global_prefix = "dd.response"
    fixed_tags = {
        "cluster": cluster,
        "hostname": hostname,
        "service_name": service_name,
    }
    doorstats_global.initialize(
        host=statsd_server, prefix=global_prefix, fixed_tags=fixed_tags
    )
    return doorstats_global


class DoorDashMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ExceptionMiddleware,
        statsd_server: str = DEFAULT_STATSD_SERVER,
        service_name: str = DEFAULT_SERVICE_NAME,
        cluster: str = DEFAULT_CLUSTER,
    ):
        self.app = app
        self.statsd_client = init_statsd(statsd_server, service_name, cluster)

    async def dispatch_func(
        self: Any, request: Request, call_next: RequestResponseEndpoint
    ):
        method = request.method
        endpoint = ""
        start_time = time.time()
        response = await call_next(request)
        latency = int((time.time() - start_time) * 1000)
        status_type = f"{response.status_code // 100}XX"

        context = get_context_from_req(request)
        context.log.info(
            "request complete",
            endpoint=endpoint,
            method=method,
            status_code=str(response.status_code),
            latency=latency,
        )

        for r in self.app.app.routes:
            if r.matches(request._scope)[0] == Match.FULL:
                endpoint = r.path.replace("{", "").replace("}", "").replace("/", "|")

        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(response.status_code),
        }

        self.statsd_client.incr(status_type, 1, tags=tags)
        self.statsd_client.timing("latency", latency, tags=tags)

        return response
