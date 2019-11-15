import abc
import asyncio
import functools
import inspect
import time
from collections import deque
from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
from types import TracebackType
from typing import (
    Any,
    Callable,
    cast,
    ContextManager,
    Deque,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
)

import pydantic
from pydantic.fields import Field
from typing_extensions import Literal

from app.commons.context.logger import root_logger as default_logger

"""
Instrumentation for application metrics.

- TrackingManagers are used to decorate classes, instances, methods, or functions.

When called on classes or instances, they wrap the methods of the class with a context manager.

- Trackers can be used to provide various tracking or timing functionality.

"""


Unspecified = type("UnspecifiedType", (object,), {})()
Trackable = type("TrackableType", (object,), {})()
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
    req_id: str = ""

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
def breadcrumb_ctxt_manager(breadcrumb: Breadcrumb, restore=True):
    token = None
    try:
        crumbs = get_breadcrumbs()
        crumb = _push_breadcrumb(crumbs, breadcrumb)
        token = BREADCRUMBS.set(crumbs)
        yield crumb
    finally:
        if token and restore:
            BREADCRUMBS.reset(token)
        _pop_breadcrumb()


def _combine_and_replace_breadcrumbs(*, src: Breadcrumb, addition: Breadcrumb):
    values = {**src.dict()}
    # only override values that are set
    values.update(addition.dict(skip_defaults=True))
    fields_set = {*src.__fields_set__, *addition.__fields_set__}
    return Breadcrumb.construct(values, fields_set)


def _push_breadcrumb(crumbs: Deque[Breadcrumb], breadcrumb: Breadcrumb) -> Breadcrumb:
    previous_crumb = Breadcrumb() if not len(crumbs) else crumbs[0]
    next_crumb = _combine_and_replace_breadcrumbs(
        src=previous_crumb, addition=breadcrumb
    )
    crumbs.appendleft(next_crumb)
    return next_crumb


def _pop_breadcrumb() -> Breadcrumb:
    stack = get_breadcrumbs()

    if len(stack) > 0:
        return stack.popleft()
    return Breadcrumb()


def trackable(func):
    """
    mark the specified method as trackable, so TrackingManager
    will create trackers for these methods when used as a decorator
    """
    func.__trackable__ = Trackable
    return func


def is_trackable(func):
    """
    determine whether the function is marked as trackable
    """
    return getattr(func, "__trackable__", None) is Trackable


TTracker = TypeVar("TTracker", bound=ContextManager)


class TrackingManager(Generic[TTracker], metaclass=abc.ABCMeta):
    __trackable__ = Trackable
    only_trackable: bool

    def __init__(self, *, only_trackable=False):
        """
        TrackingManagers are used to decorate classes, instances, methods, or functions.

        When called on classes or instances, they wrap the methods with a context manager,
        which can be used to provide various tracking or timing functionality.

        Keyword Arguments:
            only_trackable {bool} -- (when used as a class decorator) enable tracking
                                     for methods marked with the @trackable decorator
                                     (default: {False})
        """
        self.only_trackable = only_trackable

    def process_tracker(self, tracker: TTracker):
        """
        callback receiving the tracker when it exits
        """
        ...

    @abc.abstractmethod
    def create_tracker(
        self,
        obj: Any = Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> TTracker:
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

    def _start_tracker(
        self, stack: ExitStack, *, obj=Unspecified, func, args, kwargs
    ) -> TTracker:
        # NOTE: context manager exits are called in reverse order
        tracker = self.create_tracker(obj=obj, func=func, args=args, kwargs=kwargs)
        # process_tracker callback is the last thing called,
        # will be called even if the exception is not suppressed
        stack.callback(self.process_tracker, tracker)
        # enter the context manager; __exit__ callback will be called
        stack.enter_context(tracker)
        return tracker

    def _exit_tracker(self, tracker, result):
        """
        should be called with the result of the function, if any
        """
        try:
            if isinstance(tracker, BaseTracker):
                tracker.process_result(result)
        except Exception:
            default_logger.warn("exception occurred processing tracker", exc_info=True)

    def _sync_wrapper(self, *, obj=Unspecified, func, args, kwargs):
        with ExitStack() as stack:
            tracker = self._start_tracker(
                stack, obj=obj, func=func, args=args, kwargs=kwargs
            )
            # get and process the result; suppress any issues processing
            result = func(*args, **kwargs)
            self._exit_tracker(tracker, result)
            return result

    async def _async_wrapper(self, *, obj=Unspecified, func, args, kwargs):
        with ExitStack() as stack:
            tracker = self._start_tracker(
                stack, obj=obj, func=func, args=args, kwargs=kwargs
            )
            # get and process the result; suppress any issues processing
            result = await func(*args, **kwargs)
            self._exit_tracker(tracker, result)
            return result

    def _decorate_class_method(self, func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                obj = args[0]
                return await self._async_wrapper(
                    obj=obj, func=func, args=args, kwargs=kwargs
                )

            async_wrapper.__trackable__ = Trackable

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                obj = args[0]
                return self._sync_wrapper(obj=obj, func=func, args=args, kwargs=kwargs)

            sync_wrapper.__trackable__ = Trackable

            return sync_wrapper

    def _decorate_method(self, func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                obj = getattr(func, "__self__", Unspecified)
                return await self._async_wrapper(
                    obj=obj, func=func, args=args, kwargs=kwargs
                )

            async_wrapper.__trackable__ = Trackable

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                obj = getattr(func, "__self__", Unspecified)
                return self._sync_wrapper(obj=obj, func=func, args=args, kwargs=kwargs)

            sync_wrapper.__trackable__ = Trackable

            return sync_wrapper

    def _decorate_func(self, func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._async_wrapper(func=func, args=args, kwargs=kwargs)

            async_wrapper.__trackable__ = Trackable

            return async_wrapper

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._sync_wrapper(func=func, args=args, kwargs=kwargs)

            sync_wrapper.__trackable__ = Trackable

            return sync_wrapper


class BreadcrumbManager(TrackingManager):
    breadcrumb: Breadcrumb
    from_kwargs: Dict[str, str]

    def __init__(
        self,
        breadcrumb: Breadcrumb,
        *,
        from_kwargs: Optional[Dict[str, str]] = None,
        only_trackable=False,
    ):
        """
        :param breadcrumb:
        :param from_kwargs:
        :param only_trackable:
        """
        super().__init__(only_trackable=only_trackable)
        self.breadcrumb = breadcrumb
        self.from_kwargs = from_kwargs or {}
        BreadcrumbManager.validate_from_kwargs(self.from_kwargs)

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
        obj=Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> ContextManager:
        initial_breadcrumb = self.breadcrumb
        additional_breadcrumb = BreadcrumbManager.breadcrumb_from_kwargs(
            self.from_kwargs, kwargs
        )
        combined_breadcrumb = _combine_and_replace_breadcrumbs(
            src=initial_breadcrumb, addition=additional_breadcrumb
        )
        return breadcrumb_ctxt_manager(combined_breadcrumb)


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
    req_id: Optional[str] = None,
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
    if req_id is not None:
        kwargs["req_id"] = req_id

    return BreadcrumbManager(
        Breadcrumb(**kwargs), from_kwargs=from_kwargs, only_trackable=only_trackable
    )


class BaseTracker(ContextManager):
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[Literal[False]]:
        # trackers should not suppress exceptions
        return False

    def process_result(self, result: Any):
        """
        callback receiving the result of the wrapped function call
        """
        ...


class BaseTimer(BaseTracker):
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

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[Literal[False]]:
        # stop timing
        self.end_counter = time.perf_counter()
        return False


TManager = TypeVar("TManager", bound="TimingManager")
TTimer = TypeVar("TTimer", bound="BaseTimer")
Processor = Callable[[TManager, TTimer], Any]


class TimingManager(Generic[TTimer], TrackingManager[TTimer]):
    send: bool

    def __init__(
        self: TManager,
        *,
        send=True,
        rate=1,
        processors: Optional[List[Processor]] = None,
        only_trackable=False,
    ):
        super(TimingManager, self).__init__(only_trackable=only_trackable)
        self.rate = rate
        self.send = send
        if processors is not None:
            self.processors = processors or []
        self.only_trackable = only_trackable

    def create_tracker(
        self,
        obj=Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> TTimer:
        return cast(TTimer, BaseTimer())

    def process_tracker(self, timer: TTimer):
        if not self.send:
            return

        self.run_processors(self.processors, timer)

    def run_processors(self: TManager, processors: List[Processor], timer: TTimer):
        for processor in processors:
            try:
                processor(self, timer)
            except Exception:  # noqa: E722
                default_logger.warn(
                    "exception occurred in processor %s",
                    processor.__name__,
                    exc_info=True,
                )


def get_contextvar(variable: ContextVar[T], default=Unspecified) -> T:
    if default is Unspecified:
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
