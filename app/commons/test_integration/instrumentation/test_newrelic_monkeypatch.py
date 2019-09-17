import pytest
import asyncio
from threading import current_thread
from newrelic.core.trace_cache import trace_cache
from app.commons.instrumentation.newrelic_monkeypatch import monkeypatch_for_asyncio
from app.commons.utils.pool import ThreadPoolHelper


class TestNewRelicMonkeyPatch:
    @pytest.fixture(autouse=True)
    def pool_helper(self):
        self.pool_helper = ThreadPoolHelper()
        restore = monkeypatch_for_asyncio()
        # close the threadpoolexecutor
        with self.pool_helper.executor:
            yield
        restore()

    @pytest.mark.asyncio
    async def test_task_id(self):
        task_id = id(asyncio.current_task())
        thread_id = current_thread().ident

        def run_job():
            return (trace_cache().current_thread_id(), current_thread().ident)

        current_task_id = trace_cache().current_thread_id()
        assert current_task_id == task_id, "asyncio task id is returned"
        assert current_task_id != thread_id

        job_task_id, job_thread_id = await self.pool_helper.submit(run_job)
        assert job_thread_id != thread_id, "job is running in a threadpool"
        assert job_task_id == task_id, "asyncio task id is returned in threadpool"
