from typing import NoReturn
from typing_extensions import Protocol
from structlog.stdlib import BoundLogger as Logger
from doordash_python_stats.ddstats import DoorStatsProxyMultiServer as StatsClient


class MonitoringProcessor(Protocol):
    """
    processing task that emits stats or log messages
    """

    __name__: str

    def __call__(self, __stats: StatsClient, __logger: Logger) -> NoReturn:
        ...


class PoolJobStats(Protocol):
    """
    standard stats for threadpools and other execution pools
    """

    @property
    def waiting_job_count(self) -> int:
        ...

    @property
    def total_job_count(self) -> int:
        ...

    @property
    def active_job_count(self) -> int:
        ...
