import contextlib
import functools
import sys
import structlog

from enum import Enum
from types import FrameType, TracebackType
from typing import Tuple, Any, Callable, List, Dict, Optional, Type
from typing_extensions import AsyncContextManager, Literal, Protocol, runtime_checkable
from doordash_python_stats import ddstats

from app.commons import tracing
from app.commons.timing.base import format_exc_name
from app.commons.context.logger import root_logger as default_logger
from app.commons.stats import get_service_stats_client, get_request_logger

import asyncio
import concurrent.futures

try:
    from psycopg2.errors import QueryCanceledError
except ImportError:
    from psycopg2.extensions import QueryCanceledError


@runtime_checkable
class Database(Protocol):
    database_name: str
    instance_name: str


class RequestStatus(str, Enum):
    """
    Request Status categories for Database Queries
    """

    success = "success"
    timeout = "timeout"
    error = "error"


def _discover_caller(additional_ignores=None) -> Tuple[FrameType, str]:
    """
    Remove all app.commons.tracing calls and return the relevant app frame.

    (borrowed from "structlog._frames")

    :param additional_ignores: Additional names with which the first frame must
        not start.
    :type additional_ignores: `list` of `str` or `None`

    :rtype: tuple of (frame, name)
    """
    ignores = [
        # current module
        __name__,
        # tracing module
        "app.commons.tracing",
        # context managers
        "contextlib",
    ] + (additional_ignores or [])
    f = sys._getframe()
    name = f.f_globals.get("__name__") or "?"
    while any(tuple(name.startswith(i) for i in ignores)):
        if f.f_back is None:
            name = "?"
            break
        f = f.f_back
        name = f.f_globals.get("__name__") or "?"
    return f, name


class DatabaseTimer(tracing.BaseTimer):
    database: Database
    calling_module_name: str = ""
    calling_function_name: str = ""
    stack_frame: Any = None

    request_status: str = RequestStatus.success
    exception_name: str = ""

    def __init__(self, database: Database, additional_ignores=None):
        super().__init__()
        self.database = database
        self.additional_ignores = additional_ignores

    def __enter__(self):
        super().__enter__()
        self.stack_frame, self.calling_module_name = _discover_caller(
            additional_ignores=self.additional_ignores
        )
        self.calling_function_name = self.stack_frame.f_code.co_name
        return self

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
            (
                asyncio.TimeoutError,
                asyncio.CancelledError,
                concurrent.futures.TimeoutError,
                QueryCanceledError,
            ),
        ):
            self.request_status = RequestStatus.timeout
        else:
            # something else
            self.request_status = RequestStatus.error

        return False


def track_query(func):
    return DatabaseTimingManager(message="query complete")(func)


def track_transaction(func):
    return TransactionTimingManager(message="transaction complete")(func)


def log_query_timing(tracker: "DatabaseTimingManager", timer: DatabaseTimer):
    if not isinstance(timer.database, Database):
        return
    log: structlog.stdlib.BoundLogger = get_request_logger(default=default_logger)
    breadcrumb = tracing.get_current_breadcrumb()

    # these are not currently available through context
    database = {
        "database_name": timer.database.database_name,
        "instance_name": timer.database.instance_name,
        "transaction": bool(breadcrumb.transaction_name),
        "transaction_name": breadcrumb.transaction_name,
        "request_status": timer.request_status,
    }
    caller = breadcrumb.dict(
        include={"application_name", "processor_name", "repository_name"},
        skip_defaults=True,
    )
    if timer.calling_module_name:
        caller["module_name"] = timer.calling_module_name
    if timer.exception_name:
        database["exception_name"] = timer.exception_name

    log.info(
        tracker.message,
        query=timer.calling_function_name,
        latency_ms=round(timer.delta_ms, 3),
        database=database,
        caller=caller,
    )


def log_transaction_timing(tracker: "DatabaseTimingManager", timer: DatabaseTimer):
    if not isinstance(timer.database, Database):
        return
    log: structlog.stdlib.BoundLogger = get_request_logger(default=default_logger)
    breadcrumb = tracing.get_current_breadcrumb()

    # these are not currently available through context
    database = {
        "database_name": timer.database.database_name,
        "instance_name": timer.database.instance_name,
        "request_status": timer.request_status,
    }

    caller = breadcrumb.dict(
        include={"application_name", "processor_name", "repository_name"},
        skip_defaults=True,
    )
    if timer.calling_module_name:
        caller["module_name"] = timer.calling_module_name
    if timer.exception_name:
        database["exception_name"] = timer.exception_name

    log.info(
        tracker.message,
        transaction=timer.calling_function_name,
        latency_ms=round(timer.delta_ms, 3),
        database=database,
        caller=caller,
    )


def _stat_query_timing(
    tracker: "DatabaseTimingManager", timer: DatabaseTimer, *, query_type=""
):
    if not isinstance(timer.database, Database):
        return

    stats: ddstats.DoorStatsProxyMultiServer = get_service_stats_client()
    log: structlog.stdlib.BoundLogger = get_request_logger(default=default_logger)
    breadcrumb = tracing.get_current_breadcrumb()

    stat_name = "io.db.latency"
    tags = breadcrumb.dict(
        include={
            "application_name",
            # "database_name",
            # "instance_name",
            "transaction_name",
        },
        skip_defaults=True,
    )
    if query_type:
        tags["query_type"] = query_type

    if timer.calling_function_name:
        tags["query_name"] = timer.calling_function_name

    # not yet available in breadcrumbs
    if timer.database.database_name:
        tags["database_name"] = timer.database.database_name
    if timer.database.instance_name:
        tags["instance_name"] = timer.database.instance_name

    if timer.request_status:
        tags["request_status"] = timer.request_status

    # emit stats
    stats.timing(stat_name, timer.delta_ms, tags=tags)
    log.debug("statsd: %s", stat_name, latency_ms=timer.delta_ms, tags=tags)


def stat_query_timing(tracker: "DatabaseTimingManager", timer: DatabaseTimer):
    _stat_query_timing(tracker, timer)


def stat_transaction_timing(tracker: "DatabaseTimingManager", timer: DatabaseTimer):
    _stat_query_timing(tracker, timer, query_type="transaction")


class DatabaseTimingManager(tracing.TimingManager[DatabaseTimer]):
    """
    Tracker for database queries and transactions
    """

    message: str

    log: structlog.stdlib.BoundLogger
    stats: ddstats.DoorStatsProxyMultiServer

    # database query processors
    processors = [log_query_timing, stat_query_timing]

    def __init__(self, *, message: str):
        super().__init__()
        self.message = message

    def create_tracker(
        self,
        obj=tracing.Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> DatabaseTimer:
        additional_ignores = ["app.commons.database"]
        return DatabaseTimer(database=obj, additional_ignores=additional_ignores)

    def __call__(self, func_or_class):
        # NOTE: we assume that this is only called to decorate a class
        return self._decorate_class_method(func_or_class)


class TransactionTimingManager(DatabaseTimingManager):
    # database transaction processors
    processors = [log_query_timing, stat_transaction_timing]

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            obj: Database = args[0]
            transaction_manager: AsyncContextManager = func(*args, **kwargs)

            # chain together a context managers
            @contextlib.asynccontextmanager
            async def wrapped_transaction():
                async with contextlib.AsyncExitStack() as stack:
                    # NOTE: context manager exits are called in reverse order
                    tracker: DatabaseTimer = self.create_tracker(
                        obj=obj, func=func, args=args, kwargs=kwargs
                    )
                    # process_tracker callback is the last thing called,
                    # will be called even if the exception is not suppressed
                    stack.callback(self.process_tracker, tracker)
                    # timing: start timing transaction
                    stack.enter_context(tracker)
                    # tracing: set transaction name
                    stack.enter_context(
                        tracing.breadcrumb_as(
                            tracing.Breadcrumb(
                                transaction_name=tracker.calling_function_name
                            )
                        )
                    )
                    # start transaction
                    transaction = await stack.enter_async_context(transaction_manager)
                    yield transaction

            return wrapped_transaction()

        return wrapper
