import asyncio
import contextvars
from concurrent import futures
from typing import Optional, Union

Timeout = Union[float, int]


class ThreadPoolHelper:
    prefix = ""
    executor: futures.ThreadPoolExecutor

    def __init__(self, max_workers: Optional[int] = None):
        self.executor = futures.ThreadPoolExecutor(max_workers, self.prefix)

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
