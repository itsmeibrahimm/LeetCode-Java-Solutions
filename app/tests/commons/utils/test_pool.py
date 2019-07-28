import asyncio
import time
import pytest
import logging
import threading

from app.commons.utils.pool import ThreadPoolHelper


class TestPool:
    # ensure these tests run in the event loop
    pytestmark = pytest.mark.asyncio

    @pytest.fixture
    def pool(self):
        # ensure pool is cleaned up after test run
        pool = ThreadPoolHelper(max_workers=5)
        with pool.executor:
            yield pool

    async def test_submit_single(self, pool: ThreadPoolHelper):
        def slow_task(result):
            time.sleep(0.2)
            return result

        done, pending = await asyncio.wait([pool.submit(slow_task, 1)], timeout=0.15)
        assert len(done) == 0, "slow task did not finish"
        assert len(pending) == 1, "slow task is still pending, did not get cancelled"
        pending_task = pending.pop()
        assert await pending_task == 1, "task execution continues"

    async def test_submit_concurrent(self, pool: ThreadPoolHelper):
        logger = logging.getLogger()

        def sleep_task(result):
            logger.info(
                "sleeping in thread %s, task returning %d",
                threading.current_thread().getName(),
                result,
            )
            time.sleep(0.1)
            return result

        assert await pool.submit(sleep_task, 50) == 50, "running a single task"

        # run 5 tasks, ensure they all execute concurrently (ie. within timeout)
        tasks = [pool.submit(sleep_task, i) for i in range(5)]
        done, pending = await asyncio.wait(tasks, timeout=0.15)
        assert (
            len(done) == 5
        ), "all tasks are finished within timeout when running in parallel"
        assert len(pending) == 0, "no tasks are pending"
        assert {task.result() for task in done} == set(
            range(5)
        ), "check result of tasks"

    async def test_submit_with_timeout(self, pool: ThreadPoolHelper):
        def fast_task(result):
            time.sleep(0.1)
            return result

        def slow_task(result):
            time.sleep(0.2)
            return result

        assert (
            await pool.submit_with_timeout(0.15, fast_task, 25) == 25
        ), "fast test successfully executes"
        task = pool.submit_with_timeout(0.15, slow_task, 35)
        with pytest.raises(asyncio.futures.TimeoutError):
            await task
