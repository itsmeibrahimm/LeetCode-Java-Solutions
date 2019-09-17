import asyncio
from contextvars import ContextVar

NEWRELIC_TASK_ID: ContextVar[int] = ContextVar("NEWRELIC_TASK_ID")


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
        try:
            current_task = asyncio.current_task()
            # early exit if we're not in an asyncio task
            if not current_task:
                return old_thread_id(self)
        except RuntimeError:
            # no event loop
            return old_thread_id(self)

        # get the task_id of the root task for asyncio
        task_id = NEWRELIC_TASK_ID.get(id(current_task))
        # and set it (preserving it for the entire asyncio context)
        NEWRELIC_TASK_ID.set(task_id)
        return task_id

    # apply the monkeypatch
    TraceCache.current_thread_id = monkeypatched_thread_id
