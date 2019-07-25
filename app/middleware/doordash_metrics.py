import os
import time
from doordash_python_stats.ddstats import doorstats_global
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match


DEFAULT_HOSTNAME = "unknown-hostname"
DEFAULT_CLUSTER = "unknown-cluster"
DEFAULT_SERVICE_NAME = "unknown-service"
DEFAULT_STATSD_SERVER = "prod-proxy-internal.doordash.com"


def init_statsd(app, statsd_server, service_name, cluster):
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
    app.statsd_client = doorstats_global


class DoorDashMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        statsd_server=DEFAULT_STATSD_SERVER,
        service_name=DEFAULT_SERVICE_NAME,
        cluster=DEFAULT_CLUSTER,
    ):
        self.app = app
        init_statsd(self.app, statsd_server, service_name, cluster)

    async def dispatch_func(self, request, call_next):
        method = request.method
        endpoint = ""
        start_time = time.time()
        response = await call_next(request)
        latency = int((time.time() - start_time) * 1000)
        status_type = f"{response.status_code // 100}XX"

        for r in self.app.app.routes:
            if r.matches(request._scope)[0] == Match.FULL:
                print(f"r: {r.path}")
                endpoint = r.path.replace("{", "").replace("}", "").replace("/", "|")

        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(response.status_code),
        }

        self.app.statsd_client.incr(status_type, 1, tags=tags)
        self.app.statsd_client.timing("latency", latency, tags=tags)

        return response
