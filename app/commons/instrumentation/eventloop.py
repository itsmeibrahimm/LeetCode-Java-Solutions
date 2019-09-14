import asyncio
import os
from typing import Optional
from app.commons.instrumentation.types import StatsClient, Logger


def get_running_task_count(loop: Optional[asyncio.AbstractEventLoop] = None):
    tasks = asyncio.all_tasks(loop)
    return len(tasks)


def stat_process_event_loop(stat_name="resource.event_loop.tasks"):
    """
    emit stats for the event loop task depth (per process)
    """

    def emit_event_loop_stats(stats: StatsClient, log: Logger):
        pid = os.getpid()
        count = get_running_task_count()
        stats.gauge(stat_name, count, tags={"pid": str(pid)})
        log.debug("event loop task count: %s", count, pid=pid)

    return emit_event_loop_stats
