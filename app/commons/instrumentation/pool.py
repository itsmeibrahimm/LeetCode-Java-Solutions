import os
from app.commons.instrumentation.types import PoolJobStats, StatsClient, Logger


def stat_resource_pool_jobs(
    *, stat_prefix: str, pool_name: str, pool_job_stats: PoolJobStats
):
    """
    emit per-process job stats for the specified resource pool
    """

    def emit_resource_pool_stats(stats: StatsClient, log: Logger):
        pid = os.getpid()

        tags = {"pid": str(pid), "pool_name": pool_name}
        stats.gauge(
            f"{stat_prefix}.waiting_job_count",
            pool_job_stats.waiting_job_count,
            tags=tags,
        )
        stats.gauge(
            f"{stat_prefix}.total_job_count", pool_job_stats.total_job_count, tags=tags
        )
        stats.gauge(
            f"{stat_prefix}.active_job_count",
            pool_job_stats.active_job_count,
            tags=tags,
        )

        log.debug(
            "resource pool job stats",
            resource=stat_prefix,
            pool=pool_name,
            job_stats={
                "waiting_job_count": pool_job_stats.waiting_job_count,
                "total_job_count": pool_job_stats.total_job_count,
                "active_job_count": pool_job_stats.active_job_count,
            },
        )

    return emit_resource_pool_stats


def stat_thread_pool_jobs(
    *, stat_prefix="resource.thread_pool", pool_name: str, pool_job_stats: PoolJobStats
):
    """
    emit per-process job stats for the specified thread pool executor
    """
    return stat_resource_pool_jobs(
        stat_prefix=stat_prefix, pool_name=pool_name, pool_job_stats=pool_job_stats
    )
