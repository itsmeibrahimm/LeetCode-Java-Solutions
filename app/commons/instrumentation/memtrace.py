import os
import tracemalloc
from typing import Optional
from app.commons.instrumentation.types import StatsClient, Logger


class MemTraceMonitor:
    __name__ = "monitor_mem_trace"

    stat_prefix: str
    interval_secs: float
    pid: int
    last_snapshot: Optional[tracemalloc.Snapshot]
    top: int
    key_type: str

    def __init__(
        self,
        *,
        stat_prefix: str = "resource.mem",
        interval_secs: float,
        top: int = 10,
        key_type: str = "lineno",
    ):
        self.stat_prefix = stat_prefix
        self.interval_secs = interval_secs
        self.pid = os.getpid()
        self.top = top
        self.key_type = key_type
        self.last_snapshot = None

        tracemalloc.start()

    def __call__(self, stats: StatsClient, log: Logger):
        curr_snapshot = tracemalloc.take_snapshot()

        # log the top difference
        if self.last_snapshot:
            top_stats_diff = curr_snapshot.compare_to(self.last_snapshot, self.key_type)
            log.info("malloc trace diff", diff=top_stats_diff[: self.top], pid=self.pid)

        top_stats = curr_snapshot.statistics(self.key_type)
        mem_total = sum(stat.size for stat in top_stats)

        tags = {"pid": str(self.pid)}

        # emit stats
        stats.gauge(f"{self.stat_prefix}.total_usage", mem_total, tags=tags)

        self.last_snapshot = curr_snapshot
