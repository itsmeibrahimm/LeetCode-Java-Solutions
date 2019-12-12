import asyncio
from datetime import datetime

import pytest
import pytz
from asynctest import create_autospec
from doordash_lib.runtime import Runtime
from freezegun import freeze_time

from app.commons.jobs.pool import JobPool, adjust_pool_sizes


class TestAdjustPoolSize:
    @pytest.mark.asyncio
    async def test_adjust_pool_size_by_simple_pool_size(self):
        runtime = create_autospec(Runtime)
        runtime.get_json.return_value = None

        test_pool = JobPool.create_pool(name="test", size=100)

        runtime.get_int.return_value = None
        adjust_pool_sizes(runtime)
        assert test_pool.size == 100
        runtime.get_int.return_value = 2
        adjust_pool_sizes(runtime)
        assert test_pool.size == 2

    @pytest.mark.asyncio
    async def test_adjust_pool_size_by_scheduled_pool_size(self):
        runtime = create_autospec(Runtime)
        runtime.get_int.return_value = None

        test_pool = JobPool.create_pool(name="test", size=100)
        assert test_pool.size == 100, "should has initialized size"
        assert test_pool.default_size == 100, "default size should be same as init size"

        runtime.get_json.return_value = None
        adjust_pool_sizes(runtime)
        assert test_pool.size == 100, "should has initialized size"
        assert test_pool.default_size == 100, "default size should be same as init size"

        now_pt = datetime.now(tz=pytz.timezone("US/Pacific"))

        runtime.get_json.return_value = {
            "start_hour_inclusive": now_pt.hour - 1,
            "end_hour_inclusive": now_pt.hour,
            "scheduled_size": 20,
            "timezone": str(now_pt.tzinfo),
        }
        adjust_pool_sizes(runtime)
        assert test_pool.size == 20, "should be updated to new size"

        runtime.get_json.return_value = {
            "start_hour_inclusive": now_pt.hour,
            "end_hour_inclusive": now_pt.hour,
            "scheduled_size": 30,
            "timezone": str(now_pt.tzinfo),
        }
        adjust_pool_sizes(runtime)
        assert test_pool.size == 30, "should be updated to new size"

        runtime.get_json.return_value = {
            "start_hour_inclusive": now_pt.hour - 2,
            "end_hour_inclusive": now_pt.hour - 1,
            "scheduled_size": 20,
            "timezone": str(now_pt.tzinfo),
        }
        adjust_pool_sizes(runtime)
        assert test_pool.size == test_pool.default_size, "should revert to default size"

        # 1:00 is in range of [23:00, 1:00 + 1day]
        with freeze_time(
            datetime(year=2019, month=12, day=11, hour=1, tzinfo=now_pt.tzinfo)
        ):
            runtime.get_json.return_value = {
                "start_hour_inclusive": 23,
                "end_hour_inclusive": 1,
                "scheduled_size": 50,
                "timezone": str(now_pt.tzinfo),
            }
            adjust_pool_sizes(runtime)
            assert test_pool.size == 50, "should be updated to new size"

        # 23:00 is in range of [23:00, 1:00 + 1day]
        with freeze_time(
            datetime(year=2019, month=12, day=11, hour=23, tzinfo=now_pt.tzinfo)
        ):
            runtime.get_json.return_value = {
                "start_hour_inclusive": 23,
                "end_hour_inclusive": 1,
                "scheduled_size": 60,
                "timezone": str(now_pt.tzinfo),
            }
            adjust_pool_sizes(runtime)
            assert test_pool.size == 60, "should be updated to new size"

        # 22:00 is NOT in range of [23:00, 1:00 + day]
        with freeze_time(
            datetime(year=2019, month=12, day=11, hour=22, tzinfo=now_pt.tzinfo)
        ):
            runtime.get_json.return_value = {
                "start_hour_inclusive": 23,
                "end_hour_inclusive": 1,
                "scheduled_size": 70,
                "timezone": str(now_pt.tzinfo),
            }
            adjust_pool_sizes(runtime)
            assert test_pool.size == test_pool.default_size, "should be default size"

        assert test_pool.default_size == 100, "default size should be same as init size"

    @pytest.mark.asyncio
    async def test_adjust_pool_size_when_both_config_exist(self):
        runtime = create_autospec(Runtime)
        runtime.get_int.return_value = 999

        test_pool = JobPool.create_pool(name="test", size=100)
        assert test_pool.size == 100, "should has initialized size"
        assert test_pool.default_size == 100, "default size should be same as init size"

        runtime.get_json.return_value = None
        adjust_pool_sizes(runtime)
        assert test_pool.size == 999, "should set as simple size config"

        now_pt = datetime.now(tz=pytz.timezone("US/Pacific"))

        runtime.get_json.return_value = {
            "start_hour_inclusive": now_pt.hour - 1,
            "end_hour_inclusive": now_pt.hour,
            "scheduled_size": 20,
            "timezone": str(now_pt.tzinfo),
        }
        adjust_pool_sizes(runtime)
        assert test_pool.size == 20, "should be updated to new size"

        runtime.get_json.return_value = {
            "start_hour_inclusive": now_pt.hour,
            "end_hour_inclusive": now_pt.hour,
            "scheduled_size": 30,
            "timezone": str(now_pt.tzinfo),
        }
        adjust_pool_sizes(runtime)
        assert test_pool.size == 30, "should be updated to new size"

        runtime.get_json.return_value = {
            "start_hour_inclusive": now_pt.hour - 2,
            "end_hour_inclusive": now_pt.hour - 1,
            "scheduled_size": 20,
            "timezone": str(now_pt.tzinfo),
        }
        adjust_pool_sizes(runtime)
        assert test_pool.size == 999, "should set as simple size config"
        assert test_pool.default_size == 100, "default size should be same as init size"

    @pytest.mark.asyncio
    async def test_scheduled_pool_config_malform(self):
        runtime = create_autospec(Runtime)
        runtime.get_int.return_value = None

        test_pool = JobPool.create_pool(name="test", size=100)
        assert test_pool.size == 100, "should has initialized size"
        assert test_pool.default_size == 100, "default size should be same as init size"

        now_pt = datetime.now(tz=pytz.timezone("US/Pacific"))
        runtime.get_json.return_value = {
            "start_hour_inclusive": now_pt.hour,
            "end_hour_inclusive": now_pt.hour,
            "scheduled_size": 30,
            "timezone": str(now_pt.tzinfo),
        }
        adjust_pool_sizes(runtime)
        assert test_pool.size == 30, "should be updated to new size"

        runtime.get_json.return_value = None
        adjust_pool_sizes(runtime)
        assert test_pool.size == 100, "should has initialized size"
        assert test_pool.default_size == 100, "default size should be same as init size"

        runtime.get_json.return_value = {}
        adjust_pool_sizes(runtime)
        assert test_pool.size == test_pool.default_size, "should be default size"

        runtime.get_json.return_value = {
            "start_hour_inclusive": now_pt.hour,
            "bad_key": now_pt.hour,
            "scheduled_size": 30,
            "timezone": str(now_pt.tzinfo),
        }
        adjust_pool_sizes(runtime)
        assert test_pool.size == test_pool.default_size, "should be default size"

        assert test_pool.default_size == 100, "default size should be same as init size"


class TestJobPool:
    async def update_pool_size(self, pool: JobPool, size: int, delay: float):
        await asyncio.sleep(delay)
        pool.resize(size)

    async def print_job(self, ops, n, pool: JobPool):
        ops.append(f"entering {n} pool size {pool.size}")
        await asyncio.sleep(0.1)
        ops.append(f"leaving {n} pool size {pool.size}")

    @pytest.mark.asyncio
    async def test_set_size(self):
        ops = []

        pool = JobPool(name="stripe", size=1)
        # schedule the delay right after the first job starts and finishes (0.1 + 0.01)
        asyncio.create_task(self.update_pool_size(pool=pool, size=3, delay=0.11))
        # schedule the delay back to 1 size after the next 3 jobs are enqueued, and before any of them finish (ie. within 0.1 delay of the previous delay of 0.11)
        asyncio.create_task(self.update_pool_size(pool=pool, size=1, delay=0.13))

        for i in range(1, 7):
            await pool.spawn(self.print_job(ops, i, pool))

        await pool.join()

        assert ops == [
            "entering 1 pool size 1",
            "leaving 1 pool size 1",
            "entering 2 pool size 1",  # task 2 enqueued when pool size = 1
            "entering 3 pool size 3",  # task 3, 4 enqueued together after being unblocked by larger pool size
            "entering 4 pool size 3",
            "leaving 2 pool size 1",  # when task 2 finished, pool size already reduced to 1
            "leaving 3 pool size 1",
            "leaving 4 pool size 1",
            "entering 5 pool size 1",
            "leaving 5 pool size 1",
            "entering 6 pool size 1",
            "leaving 6 pool size 1",
        ]
