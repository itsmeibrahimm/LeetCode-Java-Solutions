import asyncio
import os
import time

from typing import Optional

from app.commons.instrumentation.types import StatsClient, Logger


def get_running_task_count(loop: Optional[asyncio.AbstractEventLoop] = None):
    tasks = asyncio.all_tasks(loop)
    return len(tasks)


class EventLoopMonitor:
    __name__ = "monitor_event_loop"

    stat_prefix: str
    interval_secs: float
    pid: int
    last_called: float = 0

    def __init__(
        self, *, stat_prefix: str = "resource.event_loop", interval_secs: float
    ):
        self.stat_prefix = stat_prefix
        self.interval_secs = interval_secs
        self.pid = os.getpid()

    def __call__(self, stats: StatsClient, log: Logger):
        current_counter = time.perf_counter()

        # called for the first time, nothing to report
        if self.last_called == 0:
            self.last_called = current_counter
            return

        latency_ms = (current_counter - self.last_called - self.interval_secs) * 1000.0
        task_count = get_running_task_count()
        tags = {"pid": str(self.pid)}

        # emit stats
        stats.timing(f"{self.stat_prefix}.latency", latency_ms, tags=tags)
        stats.gauge(f"{self.stat_prefix}.task_count", task_count, tags=tags)

        log.debug(
            "event loop: latency=%0.3fms, task_count=%d",
            latency_ms,
            task_count,
            pid=self.pid,
        )

        self.last_called = current_counter
