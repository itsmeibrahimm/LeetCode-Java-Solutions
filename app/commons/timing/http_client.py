import abc
from enum import Enum
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Type

import requests
import structlog
from aiohttp import ClientResponse
from doordash_python_stats import ddstats
from typing_extensions import Literal

from app.commons import tracing
from app.commons.context.logger import root_logger as default_logger
from app.commons.stats import get_request_logger, get_service_stats_client
from app.commons.timing.base import format_exc_name
from app.commons.tracing import Processor


class RequestStatus(str, Enum):
    success = "success"
    client_error = "client_error"  # 4XX
    server_error = "server_error"  # 5XX
    timeout = "timeout"  # client timeout
    exception = "exception"  # client exception


class HttpClientTracker(tracing.BaseTimer, metaclass=abc.ABCMeta):
    """
    Generic tracker for HTTP Clients
    """

    status_code: str = ""
    client_request_id: str = ""

    request_status: str = RequestStatus.success
    exception_name: str = ""

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
            "req_id",
        },
        skip_defaults=True,
    )

    if timer.status_code:
        context["status_code"] = timer.status_code
    if timer.client_request_id:
        context["client_request_id"] = timer.client_request_id

    context["request_status"] = timer.request_status
    if timer.exception_name:
        context["exception_name"] = timer.exception_name

    log.info(
        "client request complete", latency_ms=round(timer.delta_ms, 3), context=context
    )


def log_stripe_http_client_timing(
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
            "req_id",
        },
        skip_defaults=True,
    )

    if timer.status_code:
        context["status_code"] = timer.status_code
    if timer.client_request_id:
        context["client_request_id"] = timer.client_request_id

    context["request_status"] = timer.request_status
    if timer.exception_name:
        context["exception_name"] = timer.exception_name

    if isinstance(timer, StripeClientTracker):
        if timer.stripe_error_code:
            context["stripe_error_code"] = timer.stripe_error_code
        if timer.stripe_decline_code:
            context["stripe_decline_code"] = timer.stripe_decline_code

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

    tags["request_status"] = timer.request_status

    stats.timing(tracker.stat_name, timer.delta_ms, tags=tags)
    log.debug("statsd: %s", tracker.stat_name, latency_ms=timer.delta_ms, tags=tags)


def stat_stripe_http_client_timing(
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

    tags["request_status"] = timer.request_status

    if isinstance(timer, StripeClientTracker):
        if timer.stripe_error_code:
            tags["stripe_error_code"] = timer.stripe_error_code
        if timer.stripe_decline_code:
            tags["stripe_decline_code"] = timer.stripe_decline_code

    stats.timing(tracker.stat_name, timer.delta_ms, tags=tags)
    log.info("statsd: %s", tracker.stat_name, latency_ms=timer.delta_ms, tags=tags)


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

    stripe_error_code: Optional[str]
    stripe_decline_code: Optional[str]

    def __init__(self):
        super(StripeClientTracker, self).__init__()
        self.stripe_error_code = None
        self.stripe_decline_code = None

    def process_result(self, result: requests.Response):
        """
        Process a requests HTTP response to get the status code
        and Request ID (from stripe)
        """
        self.status_code = str(result.status_code)

        if 400 <= result.status_code < 500:
            self.request_status = RequestStatus.client_error
        elif 500 <= result.status_code < 600:
            self.request_status = RequestStatus.server_error

        # stripe returns their request id
        self.client_request_id = result.headers.get("Request-Id", "")
        response_json = result.json()
        error_body = (
            response_json.get("error", {}) if isinstance(response_json, dict) else {}
        )
        self.stripe_decline_code = error_body.get("decline_code", None)
        self.stripe_error_code = error_body.get("code", None)

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[Literal[False]]:
        # ensure we get timing information
        super().__exit__(exc_type, exc_value, traceback)

        # no error, request is successful
        if exc_type is None:
            return False

        # record exception info
        self.exception_name = format_exc_name(exc_type)

        if isinstance(
            # known timeout errors
            exc_value,
            (requests.Timeout),
        ):
            self.request_status = RequestStatus.timeout
        else:
            # something else
            self.request_status = RequestStatus.exception

        return False


class StripeTimingManager(HttpClientTimingManager):
    processors = [log_stripe_http_client_timing, stat_stripe_http_client_timing]

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


class IdentityAioHttpTracker(HttpClientTracker):
    status_code: str = ""

    def process_result(self, result: ClientResponse):
        """
        Process a requests HTTP response to get the status code
        and Request ID (from stripe)
        """
        self.status_code = str(result.status)


class IdentityClientTimingManager(HttpClientTimingManager):
    processors = [log_http_client_timing, stat_http_client_timing]
    """
    Manages two stats for this client io / security
    """

    def __init__(
        self,
        *,
        stat_name: str,
        send=True,
        rate=1,
        processors: Optional[List[Processor]] = None,
        only_trackable=False,
    ):
        super().__init__(
            stat_name=stat_name,
            send=send,
            rate=rate,
            processors=processors,
            only_trackable=only_trackable,
        )

    def create_tracker(
        self,
        obj=tracing.Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> HttpClientTracker:
        return IdentityAioHttpTracker()


def track_identity_http_client_timing(**kwargs):
    return IdentityClientTimingManager(**kwargs)


def stat_identity_client_security(
    tracker: "IdentityClientSecurityManager", timer: "IdentityAioSecurityTracker"
):
    """
    emit stats for identity client requests
    """
    log: structlog.stdlib.BoundLogger = get_request_logger(default=default_logger)
    stats: ddstats.DoorStatsProxyMultiServer = get_service_stats_client()

    tags = timer.breadcrumb.dict(
        include={"application_name", "provider_name", "action", "resource"},
        skip_defaults=True,
    )
    tags["status_code"] = timer.status_code
    stats.incr(tracker.stat_name, tags=tags)
    log.debug("statsd: %s", tracker.stat_name, tags=tags)


class IdentityAioSecurityTracker(tracing.BaseTimer):
    status_code: str = "UNKNOWN"

    def process_result(self, result: ClientResponse):
        """
        Process a requests HTTP response to get the status code
        and Request ID (from stripe)
        """
        self.status_code = str(result.status)


class IdentityClientSecurityManager(tracing.TimingManager[IdentityAioSecurityTracker]):
    stat_name: str
    processors = [stat_identity_client_security]

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

    def create_tracker(
        self,
        obj=tracing.Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> IdentityAioSecurityTracker:
        return IdentityAioSecurityTracker()


def track_identity_http_client_security_stats(**kwargs):
    return IdentityClientSecurityManager(**kwargs)
