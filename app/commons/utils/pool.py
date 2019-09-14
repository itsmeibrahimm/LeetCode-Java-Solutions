import asyncio
import contextvars
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Union
from threading import Semaphore
from app.commons.instrumentation.types import PoolJobStats

Timeout = Union[float, int]


class MonitoredThreadPoolExecutor(ThreadPoolExecutor, PoolJobStats):
    """
    ThreadPoolExecutor with additional metrics
    """

    # use Semaphore as a thread-safe counter; in python 3.8 a Semaphore
    # is used to count idle threads in the TheadPoolExecutor
    _waiting_count: Semaphore
    _total_count: Semaphore

    def __init__(
        self, max_workers=None, thread_name_prefix="", initializer=None, initargs=()
    ):
        super().__init__(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix,
            initializer=initializer,
            initargs=initargs,
        )
        # number of tasks waiting to be executed
        self._waiting_count = Semaphore(0)
        # number of tasks that are active
        self._total_count = Semaphore(0)

    def _run_task_wrapper(self, fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # decrement waiting count when task is dequeued
            self._waiting_count.acquire(False)
            try:
                return fn(*args, **kwargs)
            finally:
                # decrement active count when task is finished
                self._total_count.acquire(False)

        return wrapper

    def submit(self, fn, *args, **kwargs):
        # increase the counters on enqueue
        self._waiting_count.release()
        self._total_count.release()
        # decrease the counters when we actually execute the task
        task = self._run_task_wrapper(fn)
        return super().submit(task, *args, **kwargs)

    @property
    def waiting_job_count(self) -> int:
        """
        number of jobs waiting in the pool
        """
        # looking into semaphore internals :)
        return self._waiting_count._value  # type: ignore

    @property
    def total_job_count(self) -> int:
        """
        total jobs (active and waiting)
        """
        return self._total_count._value  # type: ignore

    @property
    def active_job_count(self) -> int:
        """
        active job count (currently executing)
        """
        # NOTE: this can be replaced with `self._idle_semaphore` in python 3.8
        return self.total_job_count - self.waiting_job_count


class ThreadPoolHelper:
    prefix = ""
    executor: MonitoredThreadPoolExecutor

    def __init__(self, max_workers: Optional[int] = None, prefix: str = ""):
        self.prefix = prefix
        self.executor = MonitoredThreadPoolExecutor(max_workers, self.prefix)

    def shutdown(self, wait=True):
        self.executor.shutdown(wait=wait)

    async def submit(self, fn, *args, **kwargs):
        """
        Submit a function for execution in the ThreadPoolExecutor, and `await` the result

        Args:
            fn: the function to be executed
            timeout: timeout for the task, in seconds; if `None`, use the default timeout on the pool

        Note that :class:`concurrent.futures.Futures` are not directly awaitable, they
        need to be wrapped in an :class:`asyncio.Future`

        This is the same code as :class:`asyncio.BaseEventLoop.run_in_executor` except that
        we can support `kwargs` more easily (`run_in_executor` only); compare:

        ::

            import functools.partial
            loop: asyncio.BaseEventLoop = asyncio.get_running_loop()
            return await loop.run_in_executor(self.executor, functools.partial(fn, **kwargs), *args)
        """
        # ensure that contextvars are preserved in the threadpool executor
        # see: https://github.com/getsentry/sentry-python/issues/162
        #
        # (this is the asyncio version of threading.local)
        # see https://github.com/encode/starlette/pull/192/files for implementation example
        context: contextvars.Context = contextvars.copy_context()

        return await asyncio.wrap_future(
            self.executor.submit(context.run, fn, *args, **kwargs)
        )

    async def submit_with_timeout(self, timeout: Timeout, fn, *args, **kwargs):
        """
        Submit a function for execution in the ThreadPoolExecutor, and `await` the result
        Cancel the execution if it does not complete with the specified `timeout`

        Args:
            timeout: timeout for the task, in seconds; if `None`, use the default timeout on the pool
            fn: the function to be executed

        Raises:
            asyncio.futures.TimeoutError: if the execution times out
            asyncio.futures.CancelledError: if the execution gets cancelled
        """
        context: contextvars.Context = contextvars.copy_context()
        return await asyncio.wait_for(
            self.submit(context.run, fn, *args, **kwargs), timeout=timeout
        )
