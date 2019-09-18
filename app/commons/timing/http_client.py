import abc
from typing import Any, Callable, List, Dict, Optional

import structlog
import requests
from doordash_python_stats import ddstats

from app.commons import tracing
from app.commons.context.logger import root_logger as default_logger
from app.commons.stats import get_service_stats_client, get_request_logger
from app.commons.tracing import Processor


class HttpClientTracker(tracing.BaseTimer, metaclass=abc.ABCMeta):
    """
    Generic tracker for HTTP Clients
    """

    status_code: str = ""
    client_request_id: str = ""

    @abc.abstractmethod
    def process_result(self, result):
        """
        Process the result of the Client Request (HTTP Response)
        for the status_code and client_request_id, if available
        """
        ...


def log_http_client_timing(
    tracker: "HttpClientTimingManager", timer: HttpClientTracker
):
    """
    emit logs for http client requests
    """
    log: structlog.stdlib.BoundLogger = get_request_logger(default=default_logger)

    context = timer.breadcrumb.dict(
        include={
            "application_name",
            "provider_name",
            "action",
            "resource",
            "status_code",
            "country",
        },
        skip_defaults=True,
    )
    if timer.status_code:
        context["status_code"] = timer.status_code
    if timer.client_request_id:
        context["client_request_id"] = timer.client_request_id
    log.info(
        "client request complete", latency_ms=round(timer.delta_ms, 3), context=context
    )


def stat_http_client_timing(
    tracker: "HttpClientTimingManager", timer: HttpClientTracker
):
    """
    emit stats for http client requests
    """
    log: structlog.stdlib.BoundLogger = get_request_logger(default=default_logger)
    stats: ddstats.DoorStatsProxyMultiServer = get_service_stats_client()

    tags = timer.breadcrumb.dict(
        include={
            "application_name",
            "provider_name",
            "action",
            "resource",
            "status_code",
            "country",
        },
        skip_defaults=True,
    )
    if timer.status_code:
        tags["status_code"] = timer.status_code
    stats.timing(tracker.stat_name, timer.delta_ms, tags=tags)
    log.debug("statsd: %s", tracker.stat_name, latency_ms=timer.delta_ms, tags=tags)


class HttpClientTimingManager(
    tracing.TimingManager[HttpClientTracker], metaclass=abc.ABCMeta
):
    """
    Generic Timing Manager for HTTP Clients
    """

    stat_name: str
    processors = [log_http_client_timing, stat_http_client_timing]

    def __init__(
        self,
        *,
        stat_name: str,
        send=True,
        rate=1,
        processors: Optional[List[Processor]] = None,
        only_trackable=False,
    ):
        self.stat_name = stat_name
        super().__init__(
            send=send, rate=rate, processors=processors, only_trackable=only_trackable
        )

    @abc.abstractmethod
    def create_tracker(
        self,
        obj=tracing.Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> HttpClientTracker:
        ...


class StripeClientTracker(HttpClientTracker):
    status_code: str = ""
    client_request_id: str = ""

    def process_result(self, result: requests.Response):
        """
        Process a requests HTTP response to get the status code
        and Request ID (from stripe)
        """
        self.status_code = str(result.status_code)
        # stripe returns their request id
        self.client_request_id = result.headers.get("Request-Id", "")


class StripeTimingManager(HttpClientTimingManager):
    processors = [log_http_client_timing, stat_http_client_timing]

    def create_tracker(
        self,
        obj=tracing.Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> HttpClientTracker:
        return StripeClientTracker()


def track_stripe_http_client(**kwargs):
    return StripeTimingManager(**kwargs)
