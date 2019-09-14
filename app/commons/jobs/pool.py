from typing import List

from asyncio_pool import AioPool

# Pool that should be used if the job makes a call to Stripe
from app.commons.instrumentation.types import PoolJobStats


class JobPool(AioPool, PoolJobStats):

    pools: List["JobPool"] = []

    def __init__(self, size=1024, *, name: str, loop=None):
        self.name = name
        super().__init__(size, loop=loop)

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
