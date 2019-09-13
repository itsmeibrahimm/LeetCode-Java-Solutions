from typing import List

from asyncio_pool import AioPool

# Pool that should be used if the job makes a call to Stripe
from doordash_python_stats.ddstats import DoorStatsProxyMultiServer


class JobPool(AioPool):

    pools: List["JobPool"] = []

    def __init__(self, size=1024, *, name: str, loop=None):
        self.name = name
        super().__init__(size, loop=loop)

    @classmethod
    def create_pool(cls, *args, **kwargs):
        pool = cls(*args, **kwargs)
        cls.pools.append(pool)
        return pool


async def monitor_pools(statsd_client: DoorStatsProxyMultiServer):
    """

    Monitors the size of job pools

    :return:
    """
    for pool in JobPool.pools:
        tags = {"pool": pool.name}
        statsd_client.gauge(
            "job_pools.waiting_job_count", len(pool._waiting), tags=tags
        )
        statsd_client.gauge("job_pools.active_job_count", pool.n_active, tags=tags)
        statsd_client.gauge("job_pools.total_job_count", len(pool), tags=tags)
