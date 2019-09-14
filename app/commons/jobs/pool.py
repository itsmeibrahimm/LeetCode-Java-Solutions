from typing import List

from asyncio_pool import AioPool

# Pool that should be used if the job makes a call to Stripe
from doordash_lib.runtime import Runtime

from app.commons.instrumentation.types import PoolJobStats

from app.commons.context.logger import get_logger
from app.commons.jobs.semaphore import ResizableSemaphore

logger = get_logger()


class JobPool(AioPool, PoolJobStats):

    pools: List["JobPool"] = []

    def __init__(self, size=1024, *, name: str, loop=None):
        super().__init__(size, loop=loop)
        self.name = name
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


def adjust_pool_sizes(runtime: Runtime):
    """
    Adjusts pool sizes based on values in runtime

    :param runtime:
    :return:
    """
    for pool in JobPool.pools:
        new_pool_size = runtime.get_int(f"job_pools/{pool.name}.int", None)
        if new_pool_size and new_pool_size != pool.size:
            old_size = pool.size
            logger.info(
                "Adjusting job pool size",
                pool_name=pool.name,
                old_size=old_size,
                new_size=new_pool_size,
            )
            pool.resize(new_pool_size)
