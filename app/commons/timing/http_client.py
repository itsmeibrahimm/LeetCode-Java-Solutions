import abc
from enum import Enum
from types import TracebackType
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, ClassVar

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


class HttpClientTimer(tracing.BaseTimer, metaclass=abc.ABCMeta):
    """
    Generic timing tracker for HTTP Clients
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

    def get_log_context(self) -> Dict[str, Any]:
        """
        Return a dict contains all context can be used for logging.
        for example, {"application_name":"payment-service", "resource":"paymentaccount"}
        """
        context = self._common_context()
        context["req_id"] = self.breadcrumb.req_id

        if self.client_request_id:
            context["client_request_id"] = self.client_request_id

        if self.exception_name:
            context["exception_name"] = self.exception_name
        return context

    def get_stat_tags(self) -> Dict[str, Any]:
        """
        Return a dict contains point tags that can be used to emit stats.
        """
        return self._common_context()

    def _common_context(self) -> Dict[str, Any]:
        """
        Return base context as a dict for logging or stats use.
        !!Note!! DO NOT put any key with high cardinality values (e.g. req_id) in this base dimension
        as it will explode our metrics
        """

        context = self.breadcrumb.dict(
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

        if self.status_code:
            context["status_code"] = self.status_code

        context["request_status"] = self.request_status

        return context


def log_http_client_timing(
    timing_manager: "HttpClientTimingManager", timer: HttpClientTimer
):
    """
    emit logs for http client requests
    """
    log: structlog.stdlib.BoundLogger = get_request_logger(default=default_logger)

    log_context = timer.get_log_context()

    log.info(
        "client request complete",
        latency_ms=round(timer.delta_ms, 3),
        context=log_context,
    )


def stat_http_client_timing(
    timing_manager: "HttpClientTimingManager", timer: HttpClientTimer
):
    """
    emit stats for http client requests
    """
    log: structlog.stdlib.BoundLogger = get_request_logger(default=default_logger)
    stats: ddstats.DoorStatsProxyMultiServer = get_service_stats_client()

    stats_tags = timer.get_stat_tags()

    stats.timing(timing_manager.stat_name, timer.delta_ms, tags=stats_tags)
    log.debug(
        "statsd: %s",
        timing_manager.stat_name,
        latency_ms=timer.delta_ms,
        tags=stats_tags,
    )


THttpClientTimer = TypeVar("THttpClientTimer", bound=HttpClientTimer)


class HttpClientTimingManager(
    Generic[THttpClientTimer],
    tracing.TimingManager[THttpClientTimer],
    metaclass=abc.ABCMeta,
):
    """
    Generic Timing Manager for HTTP Clients
    """

    stat_name: str

    default_processors: ClassVar[
        List[Callable[["HttpClientTimingManager", HttpClientTimer], Any]]
    ] = [log_http_client_timing, stat_http_client_timing]

    def __init__(
        self,
        *,
        stat_name: str,
        send=True,
        rate=1,
        processors: Optional[List[Processor]] = None,
        only_trackable=False,
    ):
        processors = processors or HttpClientTimingManager.default_processors
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
    ) -> THttpClientTimer:
        ...


class StripeClientTimer(HttpClientTimer):

    stripe_error_code: Optional[str]
    stripe_decline_code: Optional[str]
    stripe_error_type: Optional[str]
    stripe_error_message: Optional[str]

    def __init__(self):
        super(StripeClientTimer, self).__init__()
        self.stripe_error_code = None
        self.stripe_decline_code = None
        self.stripe_error_type = None
        self.stripe_error_message = None

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
        self.stripe_error_type = error_body.get("type", None)
        self.stripe_error_message = error_body.get("message", None)

    def get_log_context(self) -> Dict[str, Any]:
        context = super().get_log_context()
        if self.stripe_error_code:
            context["stripe_error_code"] = self.stripe_error_code
        if self.stripe_decline_code:
            context["stripe_decline_code"] = self.stripe_decline_code
        if self.stripe_error_type:
            context["stripe_error_type"] = self.stripe_error_type
        if self.stripe_error_message:
            context["stripe_error_message"] = self.stripe_error_message
        return context

    def get_stat_tags(self) -> Dict[str, Any]:
        tags = super().get_stat_tags()
        if self.stripe_error_code:
            tags["stripe_error_code"] = self.stripe_error_code
        if self.stripe_decline_code:
            tags["stripe_decline_code"] = self.stripe_decline_code
        if self.stripe_error_type:
            tags["stripe_error_type"] = self.stripe_error_type
        return tags

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


class StripeTimingManager(HttpClientTimingManager[StripeClientTimer]):
    def create_tracker(
        self,
        obj=tracing.Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> StripeClientTimer:
        return StripeClientTimer()


def track_stripe_http_client(**kwargs):
    return StripeTimingManager(**kwargs)


class IdentityAioHttpTimer(HttpClientTimer):
    status_code: str = ""

    def process_result(self, result: ClientResponse):
        """
        Process a requests HTTP response to get the status code
        and Request ID (from stripe)
        """
        self.status_code = str(result.status)


class IdentityClientTimingManager(HttpClientTimingManager[IdentityAioHttpTimer]):
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
    ) -> IdentityAioHttpTimer:
        return IdentityAioHttpTimer()


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
