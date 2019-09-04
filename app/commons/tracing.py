import abc
import asyncio
import functools
import inspect
import time

from typing import TypeVar, Generic, Any, List, Callable, ContextManager
from contextlib import contextmanager
from contextvars import ContextVar

from app.commons.context.logger import root_logger as default_logger

"""
Instrumentation for application metrics.

- Trackers: instrument context managers for timing and other purposes
- Timers: instantiated as context managers per-transaction
"""


class NotSpecifiedType:
    ...


class TrackableType:
    ...


NotSpecified = NotSpecifiedType()
Trackable = TrackableType()
T = TypeVar("T")

# Service Cotnext
APPLICATION_NAME: ContextVar[str] = ContextVar("APPLICATION_NAME", default="")
PROCESSOR_NAME: ContextVar[str] = ContextVar("PROCESSOR_NAME", default="")
REPOSITORY_NAME: ContextVar[str] = ContextVar("REPOSITORY_NAME", default="")

# Database Context
DATABASE_NAME: ContextVar[str] = ContextVar("DATABASE_NAME", default="")
INSTANCE_NAME: ContextVar[str] = ContextVar("INSTANCE_NAME", default="")
TRANSACTION_NAME: ContextVar[str] = ContextVar("TRANSACTION_NAME", default="")
METHOD_NAME: ContextVar[str] = ContextVar("METHOD_NAME", default="")


def trackable(func):
    """
    when using the class decorator variant of ContextVarDecorator,
    mark the specified method as trackable
    """
    func.__trackable__ = Trackable
    return func


def is_trackable(func):
    """
    determine whether the function is marked as trackable
    """
    return getattr(func, "__trackable__", None) is Trackable


class Tracker(metaclass=abc.ABCMeta):
    __trackable__ = Trackable
    only_trackable: bool

    def __init__(self, *, only_trackable=True):
        """
        Tracking helper to manage context.
        Can be used as a method decorator, class decorator

        Keyword Arguments:
            only_trackable {bool} -- (when used as a class decorator) enable tracking
                                     for methods marked with the @trackable decorator
                                     (default: {True})
        """
        self.only_trackable = only_trackable

    @abc.abstractmethod
    def create_tracker(self, obj: Any = NotSpecified) -> ContextManager:
        """
        Generate a tracker
        """
        ...

    def __call__(self, func_or_class):
        if inspect.isclass(func_or_class):
            # when called as a class decorator, apply to all functions (methods)
            members = inspect.getmembers(
                func_or_class,
                lambda f: inspect.isfunction(f) and not inspect.isbuiltin(f),
            )

            for member_name, member in members:
                if self.only_trackable and not is_trackable(member):
                    continue
                setattr(func_or_class, member_name, self._decorate_class_method(member))
        elif inspect.ismethod(func_or_class):
            # class instance
            return self._decorate_method(func_or_class)
        elif not inspect.isfunction(func_or_class):
            # when called on an instance, apply to all methods
            members = inspect.getmembers(func_or_class, inspect.ismethod)

            for member_name, member in members:
                if self.only_trackable and not is_trackable(member):
                    continue
                setattr(func_or_class, member_name, self._decorate_method(member))
        else:
            # when called as a function decorator
            return self._decorate_func(func_or_class)

        # class or instance
        return func_or_class

    def _decorate_class_method(self, func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(obj, *args, **kwargs):
                with self.create_tracker(obj):
                    return await func(obj, *args, **kwargs)

            async_wrapper.__trackable__ = Trackable

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(obj, *args, **kwargs):
                with self.create_tracker(obj):
                    return func(obj, *args, **kwargs)

            sync_wrapper.__trackable__ = Trackable

            return sync_wrapper

    def _decorate_method(self, func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                obj = getattr(func, "__self__", NotSpecified)
                with self.create_tracker(obj):
                    return await func(*args, **kwargs)

            async_wrapper.__trackable__ = Trackable

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                obj = getattr(func, "__self__", NotSpecified)
                with self.create_tracker(obj):
                    return func(*args, **kwargs)

            sync_wrapper.__trackable__ = Trackable

            return sync_wrapper

    def _decorate_func(self, func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.create_tracker():
                    return await func(*args, **kwargs)

            async_wrapper.__trackable__ = Trackable

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.create_tracker():
                    return func(*args, **kwargs)

            sync_wrapper.__trackable__ = Trackable

            return sync_wrapper


class ContextVarTracker(Tracker, Generic[T]):
    """
    Helper class to set/restore ContextVars.
    Can be called as a method decorator, as context manager, or on a class.
    """

    variable: ContextVar[T]
    value: T

    def __init__(self, variable: ContextVar[T], value: T, *, only_trackable=True):
        """
        ContextVar helper to manage contextually setting the contextvar;
        can be used as a method decorator, class decorator, or context manager.

        Arguments:
            variable {ContextVar[T]} -- ContextVar to set/restore
            value {T} -- value to set for the contextvar

        Keyword Arguments:
            only_trackable {bool} -- (when used as a class decorator) enable tracking
                                     for methods marked with the @trackable decorator
                                     (default: {True})
        """
        self.variable = variable
        self.value = value
        self.only_trackable = only_trackable

    def create_tracker(self, obj: Any = NotSpecified) -> ContextManager:
        return contextvar_as(self.variable, self.value)


class Timer(ContextManager):
    start_time: float = 0
    start_counter: float = 0
    end_counter: float = 0

    @property
    def delta(self):
        return (
            self.end_counter - self.start_counter
            if self.end_counter > self.start_counter
            else 0
        )

    @property
    def delta_ms(self):
        return self.delta * 1000.0

    def __enter__(self):
        self.start_time = time.time()
        self.start_counter = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_counter = time.perf_counter()


class MetricTimer(Timer):
    def __init__(self, send_metrics: Callable[["MetricTimer"], None]):
        self.send_metrics = send_metrics

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)
        self.send_metrics(self)


TT = TypeVar("TT", bound="TimingTracker")
Processor = Callable[[TT, T], None]


class TimingTracker(Generic[T], Tracker):
    send: bool
    processors: List[Processor] = []

    def __init__(
        self,
        *,
        send=True,
        rate=1,
        throttled_processors: List[Processor] = None,
        processors: List[Processor] = None,
        only_trackable=True,
    ):
        self.rate = rate
        self.send = send
        if processors is not None:
            self.processors = processors or []
        self.only_trackable = only_trackable

    def create_tracker(self, obj=NotSpecified) -> MetricTimer:
        return MetricTimer(self.process_metrics)

    def process_metrics(self, timer: MetricTimer):
        if not self.send:
            return

        self.run_processors(self.processors, timer)

    def run_processors(self, processors: List[Processor], timer: MetricTimer):
        for processor in processors:
            try:
                processor(self, timer)
            except Exception:  # noqa: E722
                default_logger.warn(
                    "exception occured in processor %s",
                    processor.__name__,
                    exc_info=True,
                )


def get_contextvar(variable: ContextVar[T], default=NotSpecified) -> T:
    if default is NotSpecified:
        return variable.get()
    return variable.get(default)


@contextmanager
def contextvar_as(variable: ContextVar[T], value: T):
    try:
        token = variable.set(value)
        yield
    finally:
        variable.reset(token)


# Service
get_app_name = functools.partial(get_contextvar, APPLICATION_NAME)
get_processor_name = functools.partial(get_contextvar, PROCESSOR_NAME)
get_repository_name = functools.partial(get_contextvar, REPOSITORY_NAME)

set_app_name = functools.partial(ContextVarTracker[str], APPLICATION_NAME)
set_processor_name = functools.partial(ContextVarTracker[str], PROCESSOR_NAME)
set_repository_name = functools.partial(ContextVarTracker[str], REPOSITORY_NAME)


# Database
get_database_name = functools.partial(get_contextvar, DATABASE_NAME)
get_instance_name = functools.partial(get_contextvar, INSTANCE_NAME)
get_transaction_name = functools.partial(get_contextvar, TRANSACTION_NAME)
get_method_name = functools.partial(get_contextvar, METHOD_NAME)

set_database_name = functools.partial(ContextVarTracker[str], DATABASE_NAME)
set_instance_name = functools.partial(ContextVarTracker[str], INSTANCE_NAME)
set_transaction_name = functools.partial(ContextVarTracker[str], TRANSACTION_NAME)
set_method_name = functools.partial(ContextVarTracker[str], METHOD_NAME)
