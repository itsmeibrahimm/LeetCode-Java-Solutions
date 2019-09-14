import asyncio

import pytest
from asynctest import create_autospec
from doordash_lib.runtime import Runtime

from app.commons.jobs.pool import JobPool, adjust_pool_sizes


class TestAdjustPoolSize:
    @pytest.mark.asyncio
    async def test_adjust_pool_size(self):
        test_pool = JobPool.create_pool(name="test", size=100)
        runtime = create_autospec(Runtime)
        runtime.get_int.return_value = None
        adjust_pool_sizes(runtime)
        assert test_pool.size == 100
        runtime.get_int.return_value = 2
        adjust_pool_sizes(runtime)
        assert test_pool.size == 2


class TestJobPool:
    async def update_pool_size(self, pool: JobPool, size: int, delay: float):
        await asyncio.sleep(delay)
        pool.resize(size)

    async def print_job(self, ops, n):
        ops.append(f"entering {n}")
        await asyncio.sleep(0.1)
        ops.append(f"leaving {n}")

    @pytest.mark.asyncio
    async def test_set_size(self):
        ops = []

        pool = JobPool(name="stripe", size=1)
        # schedule the delay right after the first job starts and finishes (0.1 + 0.01)
        asyncio.create_task(self.update_pool_size(pool=pool, size=3, delay=0.11))
        # schedule the delay back to 1 size after the next 3 jobs are enqueued, and before any of them finish (ie. within 0.1 delay of the previous delay of 0.11)
        asyncio.create_task(self.update_pool_size(pool=pool, size=1, delay=0.13))

        for i in range(1, 7):
            await pool.spawn(self.print_job(ops, i))

        await pool.join()

        assert ops == [
            "entering 1",
            "leaving 1",
            "entering 2",
            "entering 3",
            "entering 4",
            "leaving 2",
            "leaving 3",
            "leaving 4",
            "entering 5",
            "leaving 5",
            "entering 6",
            "leaving 6",
        ]
