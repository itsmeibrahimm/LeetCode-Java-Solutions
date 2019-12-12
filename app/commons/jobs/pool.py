import datetime
from typing import ClassVar, List, Optional

import pytz
from asyncio_pool import AioPool

# Pool that should be used if the job makes a call to Stripe
from doordash_lib.runtime import Runtime
from pydantic import BaseModel, validator

from app.commons.context.logger import get_logger
from app.commons.instrumentation.types import PoolJobStats
from app.commons.jobs.semaphore import ResizableSemaphore

logger = get_logger()


class JobPool(AioPool, PoolJobStats):
    pools: ClassVar[List["JobPool"]] = []

    default_size: int

    def __init__(self, size=1024, *, name: str, loop=None):
        super().__init__(size, loop=loop)
        self.name = name
        self.default_size = size
        self.semaphore = ResizableSemaphore(value=size, loop=self.loop)

    @classmethod
    def create_pool(cls, *args, **kwargs):
        pool = cls(*args, **kwargs)
        cls.pools.append(pool)
        return pool

    @property
    def waiting_job_count(self):
        return len(self._waiting)

    @property
    def active_job_count(self):
        return self.n_active

    @property
    def total_job_count(self):
        return len(self)

    def resize(self, target_size: int):
        """
        Re-set the size of the pool

        Note: target_size will only affect jobs that haven't already been spawned and let through by the Semaphore

        :param target_size:
        :return:
        """
        self.size = target_size
        self.semaphore.resize(self.size)


class ScheduledJobPoolSize(BaseModel):
    start_hour_inclusive: int
    end_hour_inclusive: int
    scheduled_size: int
    timezone: str

    @validator("timezone")
    def validate_timezone(cls, v) -> str:
        try:
            pytz.timezone(v)
        except Exception as e:
            raise ValueError(f"invalid timezone={v}") from e
        return v

    @validator("start_hour_inclusive")
    def validate_start_hour_inclusive(cls, v) -> int:
        if isinstance(v, int) and 0 <= v <= 23:
            return v
        raise ValueError(f"invalid start_hour_inclusive={v}")

    @validator("end_hour_inclusive")
    def validate_end_hour_inclusive(cls, v) -> int:
        if isinstance(v, int) and 0 <= v <= 23:
            return v
        raise ValueError(f"invalid end_hour_inclusive={v}")

    def get_timezone(self) -> datetime.tzinfo:
        return pytz.timezone(self.timezone)


def _get_simple_job_pool_size(runtime: Runtime, job_pool_name: str) -> Optional[int]:
    return runtime.get_int(f"job_pools/{job_pool_name}.int", None)


def _get_scheduled_job_pool_size(runtime: Runtime, job_pool_name: str) -> Optional[int]:
    data = runtime.get_json(f"job_pools/{job_pool_name}.json", {})

    scheduled_job_pool_size = None
    if data:
        try:
            scheduled_job_pool_size = ScheduledJobPoolSize.parse_obj(data)
        except Exception:
            logger.exception("Failed to parse scheduled job pool size", data=data)

    pool_size = None
    if scheduled_job_pool_size:
        zoned_now = datetime.datetime.now(tz=scheduled_job_pool_size.get_timezone())

        start_hour_inclusive = scheduled_job_pool_size.start_hour_inclusive
        end_hour_inclusive = scheduled_job_pool_size.end_hour_inclusive

        within_range: bool = False
        if start_hour_inclusive <= end_hour_inclusive:
            within_range = start_hour_inclusive <= zoned_now.hour <= end_hour_inclusive
        else:
            within_range = (start_hour_inclusive <= zoned_now.hour <= 23) or (
                0 <= zoned_now.hour <= end_hour_inclusive
            )

        pool_size = scheduled_job_pool_size.scheduled_size if within_range else None
        logger.info(
            "parsed scheduled job pool size",
            job_pool_name=job_pool_name,
            target_pool_size=pool_size,
            schedule=scheduled_job_pool_size.dict(),
        )

    return pool_size


def _get_pool_size(runtime: Runtime, job_pool_name: str) -> Optional[int]:
    simple_pool_size = _get_simple_job_pool_size(runtime, job_pool_name)
    scheduled_pool_size = _get_scheduled_job_pool_size(runtime, job_pool_name)
    if simple_pool_size and scheduled_pool_size:
        logger.error(
            "simple pool size and scheduled pool size configs both exists. honor scheduled pool size",
            job_pool_name=job_pool_name,
            scheduled_pool_size=scheduled_pool_size,
            simple_pool_size=simple_pool_size,
        )
        return scheduled_pool_size

    return simple_pool_size if simple_pool_size else scheduled_pool_size


def adjust_pool_sizes(runtime: Runtime):
    """
    Adjusts pool sizes based on values in runtime

    :param runtime:
    :return:
    """
    for pool in JobPool.pools:  # type: JobPool

        new_pool_size = _get_pool_size(runtime, pool.name) or pool.default_size

        if new_pool_size and new_pool_size != pool.size:
            old_size = pool.size
            logger.info(
                "Adjusting job pool size",
                pool_name=pool.name,
                old_size=old_size,
                new_size=new_pool_size,
            )
            pool.resize(new_pool_size)
