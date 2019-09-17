import asyncio
from typing import Optional
from contextvars import ContextVar

NEWRELIC_TASK_ID: ContextVar[Optional[int]] = ContextVar("NEWRELIC_TASK_ID")


def monkeypatch_for_asyncio():
    """
    NewRelic uses the current Asyncio Task ID or Thread ID to keep track
    of the current_transaction. However, this is not preserved through tasks
    (ie. if you await a result), so only traces within the same task currently
    get tracked.

    If we monkeypatch the helper to return the root task id, traces can
    be attributed to the proper transaction.
    """
    import newrelic

    if newrelic.version_info > [5, 0, 2, 126]:
        raise RuntimeError(
            "New Relic library has been updated; please verify that "
            "newrelic.core.trace_cache.TraceCache.current_thread_id "
            "monkeypatching is still necessary"
        )

    from newrelic.core.trace_cache import TraceCache

    # previous implementation
    old_thread_id = TraceCache.current_thread_id

    # monkeypatched method
    def monkeypatched_thread_id(self):
        # try getting the task id, we might have one even if
        # we're not in an asyncio Task if we're running in a threadpool
        task_id = NEWRELIC_TASK_ID.get(None)
        if task_id is not None:
            return task_id

        # otherwise, try getting the current task, falling
        # back to the old implementation based on thread id
        try:
            current_task = asyncio.current_task()
            # early exit if we're not in an asyncio task
            if not current_task:
                return old_thread_id(self)
        except RuntimeError:
            # no event loop
            return old_thread_id(self)

        # if we have a task, get the id and set the contextvar
        # (preserving it for the entire asyncio context)
        task_id = id(current_task)
        NEWRELIC_TASK_ID.set(task_id)
        return task_id

    # apply the monkeypatch
    TraceCache.current_thread_id = monkeypatched_thread_id

    def restore():
        TraceCache.current_thread_id = old_thread_id

    return restore
