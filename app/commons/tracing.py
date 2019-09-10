import abc
import asyncio
import functools
import inspect
import time
import pydantic

from typing import (
    TypeVar,
    Generic,
    Any,
    List,
    Callable,
    ContextManager,
    Deque,
    Optional,
    Dict,
)
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from pydantic.fields import Field

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


class Breadcrumb(pydantic.BaseModel):
    # application level hierarchy
    application_name: str = ""
    processor_name: str = ""
    repository_name: str = ""

    # datastore hierarchy
    database_name: str = ""
    instance_name: str = ""
    transaction_name: str = ""

    # request hierarchy
    provider_name: str = ""
    country: str = ""
    resource: str = ""
    action: str = ""
    status_code: str = ""  # should be string for stats

    class Config:
        allow_mutation = False
        extra = "forbid"


# Service Breadcrumbs (Latest first)
BREADCRUMBS: ContextVar[Deque[Breadcrumb]] = ContextVar("BREADCRUMBS")


def get_breadcrumbs() -> Deque[Breadcrumb]:
    crumbs = BREADCRUMBS.get(deque())
    return crumbs


def get_current_breadcrumb() -> Breadcrumb:
    crumbs = get_breadcrumbs()

    if len(crumbs) > 0:
        return crumbs[0]
    return Breadcrumb()


@contextmanager
def breadcrumb_as(breadcrumb: Breadcrumb):
    try:
        crumbs = get_breadcrumbs()
        crumb = _add_breadcrumb(crumbs, breadcrumb)
        token = BREADCRUMBS.set(crumbs)
        yield crumb
    finally:
        if token:
            BREADCRUMBS.reset(token)
        _remove_breadcrumb(crumbs)


def _merge_breadcrumbs(a: Breadcrumb, b: Breadcrumb):
    values = {**a.dict()}
    # only override values that are set
    values.update(b.dict(skip_defaults=True))
    fields_set = set([*a.__fields_set__, *b.__fields_set__])
    return Breadcrumb.construct(values, fields_set)


def _add_breadcrumb(crumbs: Deque[Breadcrumb], breadcrumb: Breadcrumb) -> Breadcrumb:
    previous_crumb = Breadcrumb() if not len(crumbs) else crumbs[0]
    next_crumb = _merge_breadcrumbs(previous_crumb, breadcrumb)
    crumbs.appendleft(next_crumb)
    return next_crumb


def _remove_breadcrumb(crumbs: Deque[Breadcrumb]) -> Breadcrumb:
    stack = get_breadcrumbs()

    if len(stack) > 0:
        return stack.popleft()
    return Breadcrumb()


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

    def __init__(self, *, only_trackable=False):
        """
        Tracking helper to manage context.
        Can be used as a method decorator, class decorator

        Keyword Arguments:
            only_trackable {bool} -- (when used as a class decorator) enable tracking
                                     for methods marked with the @trackable decorator
                                     (default: {False})
        """
        self.only_trackable = only_trackable

    @abc.abstractmethod
    def create_tracker(
        self,
        obj: Any = NotSpecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> ContextManager:
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
                with self.create_tracker(obj, func=func, args=args, kwargs=kwargs):
                    return await func(obj, *args, **kwargs)

            async_wrapper.__trackable__ = Trackable

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(obj, *args, **kwargs):
                with self.create_tracker(obj, func=func, args=args, kwargs=kwargs):
                    return func(obj, *args, **kwargs)

            sync_wrapper.__trackable__ = Trackable

            return sync_wrapper

    def _decorate_method(self, func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                obj = getattr(func, "__self__", NotSpecified)
                with self.create_tracker(obj, func=func, args=args, kwargs=kwargs):
                    return await func(*args, **kwargs)

            async_wrapper.__trackable__ = Trackable

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                obj = getattr(func, "__self__", NotSpecified)
                with self.create_tracker(obj, func=func, args=args, kwargs=kwargs):
                    return func(*args, **kwargs)

            sync_wrapper.__trackable__ = Trackable

            return sync_wrapper

    def _decorate_func(self, func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.create_tracker(func=func, args=args, kwargs=kwargs):
                    return await func(*args, **kwargs)

            async_wrapper.__trackable__ = Trackable

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.create_tracker(func=func, args=args, kwargs=kwargs):
                    return func(*args, **kwargs)

            sync_wrapper.__trackable__ = Trackable

            return sync_wrapper


class BreadcrumbTracker(Tracker):
    breadcrumb: Breadcrumb
    from_kwargs: Dict[str, str]

    def __init__(
        self,
        breadcrumb: Breadcrumb,
        *,
        from_kwargs: Optional[Dict[str, str]] = None,
        only_trackable=False,
    ):
        super().__init__(only_trackable=only_trackable)
        self.breadcrumb = breadcrumb
        self.from_kwargs = from_kwargs or {}
        BreadcrumbTracker.validate_from_kwargs(self.from_kwargs)

    @staticmethod
    def validate_from_kwargs(from_kwargs: Dict[str, str]):
        fields = Breadcrumb.__fields__
        for arg_name, dest_name in from_kwargs.items():
            if dest_name not in fields:
                raise ValueError(
                    f"`{dest_name}` is not a valid Breadcrumb field (mapping {arg_name} => {dest_name})"
                )

    @staticmethod
    def breadcrumb_from_kwargs(
        from_kwargs: Dict[str, str], kwargs: Dict[str, Any]
    ) -> Breadcrumb:
        model_fields: Dict[str, Field] = Breadcrumb.__fields__

        validated_fields = {}

        for arg_name, dest_name in from_kwargs.items():
            # silently ignore missing fields
            known_field = model_fields.get(dest_name, None)
            if not known_field or arg_name not in kwargs:
                continue

            value = kwargs[arg_name]

            # silently ignore invalid fields
            value, error = known_field.validate(value, {}, loc=dest_name)
            if error:
                continue

            # field is validated
            validated_fields[dest_name] = value

        try:
            return Breadcrumb(**validated_fields)
        except pydantic.ValidationError:
            # shouldn't happen, but in case we miss something
            # return a empty breadcrumb
            return Breadcrumb()

    def create_tracker(
        self,
        obj=NotSpecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> ContextManager:
        initial_fields = self.breadcrumb
        additional_fields = BreadcrumbTracker.breadcrumb_from_kwargs(
            self.from_kwargs, kwargs
        )
        combined_fields = _merge_breadcrumbs(initial_fields, additional_fields)
        return breadcrumb_as(combined_fields)


def track_breadcrumb(
    *,
    # application level hierarchy
    application_name: Optional[str] = None,
    processor_name: Optional[str] = None,
    repository_name: Optional[str] = None,
    # datastore hierarchy
    database_name: Optional[str] = None,
    instance_name: Optional[str] = None,
    transaction_name: Optional[str] = None,
    # request hierarchy
    provider_name: Optional[str] = None,
    country: Optional[str] = None,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    status_code: Optional[str] = None,
    # settings
    only_trackable=False,
    # extract from kwargs
    from_kwargs: Optional[Dict[str, str]] = None,
):
    kwargs = {}

    if application_name is not None:
        kwargs["application_name"] = application_name
    if processor_name is not None:
        kwargs["processor_name"] = processor_name
    if repository_name is not None:
        kwargs["repository_name"] = repository_name
    if database_name is not None:
        kwargs["database_name"] = database_name
    if instance_name is not None:
        kwargs["instance_name"] = instance_name
    if transaction_name is not None:
        kwargs["transaction_name"] = transaction_name
    if provider_name is not None:
        kwargs["provider_name"] = provider_name
    if country is not None:
        kwargs["country"] = country
    if resource is not None:
        kwargs["resource"] = resource
    if action is not None:
        kwargs["action"] = action
    if status_code is not None:
        kwargs["status_code"] = status_code

    return BreadcrumbTracker(
        Breadcrumb(**kwargs), from_kwargs=from_kwargs, only_trackable=only_trackable
    )


class Timer(ContextManager):
    start_time: float = 0
    start_counter: float = 0
    end_counter: float = 0
    breadcrumb: Breadcrumb

    def __init__(self):
        # empty breadcrumb by default
        self.breadcrumb = Breadcrumb()

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
        # ensure we preserve the latest breadcrumb when we enter the contextmanager
        self.breadcrumb = get_current_breadcrumb()

        # start timing
        self.start_time = time.time()
        self.start_counter = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # stop timing
        self.end_counter = time.perf_counter()


class MetricTimer(Timer):
    def __init__(self, send_metrics: Callable[["MetricTimer"], None]):
        super().__init__()
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
        processors: List[Processor] = None,
        only_trackable=False,
    ):
        self.rate = rate
        self.send = send
        if processors is not None:
            self.processors = processors or []
        self.only_trackable = only_trackable

    def create_tracker(
        self,
        obj=NotSpecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> MetricTimer:
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


def get_application_name(default="") -> str:
    return get_current_breadcrumb().application_name or default


def get_processor_name(default="") -> str:
    return get_current_breadcrumb().processor_name or default


def get_repository_name(default="") -> str:
    return get_current_breadcrumb().repository_name or default


# Database
def get_database_name(default="") -> str:
    return get_current_breadcrumb().database_name or default


def get_instance_name(default="") -> str:
    return get_current_breadcrumb().instance_name or default


def get_transaction_name(default="") -> str:
    return get_current_breadcrumb().transaction_name or default
