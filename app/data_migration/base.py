import time
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Dict, Generic, List, Optional, TypeVar

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer
from structlog.stdlib import BoundLogger

from app.commons.context.logger import get_logger


class ExtractedRecord(ABC):
    pass


E = TypeVar("E", bound=ExtractedRecord)


class StatsAndLogAware(ABC):
    statsd: DoorStatsProxyMultiServer
    base_tags: Dict[str, str]
    log: BoundLogger

    name: str

    def __init__(
        self,
        statsd: DoorStatsProxyMultiServer,
        additional_tags: Optional[Dict[str, str]] = None,
    ):
        self.statsd = statsd
        self.name = self.__class__.__name__
        self.base_tags = {"task_name": self.name}
        if additional_tags:
            self.base_tags.update(additional_tags)
        self.log = get_logger(self.name)

    def _stats_incr(
        self, metric_name: str, additional_tags: Optional[Dict[str, str]] = None
    ):
        tags = deepcopy(self.base_tags)
        if additional_tags:
            tags.update(additional_tags)

        self.statsd.incr(metric_name, tags=tags)

    def _stats_timing(
        self,
        metric_name: str,
        time_ms: float,
        additional_tags: Optional[Dict[str, str]] = None,
    ):
        tags = deepcopy(self.base_tags)
        if additional_tags:
            tags.update(additional_tags)

        self.statsd.timeing(metric_name, time_ms, tags=tags)

    def _stats_gauge(
        self,
        metric_name: str,
        value: float,
        additional_tags: Optional[Dict[str, str]] = None,
    ):
        tags = deepcopy(self.base_tags)
        if additional_tags:
            tags.update(additional_tags)

        self.statsd.gauge(metric_name, value, tags=tags)


class ExtractMany(Generic[E], StatsAndLogAware, ABC):
    def __init__(
        self,
        statsd: DoorStatsProxyMultiServer,
        additional_tags: Optional[Dict[str, str]] = None,
    ):
        super().__init__(statsd=statsd, additional_tags=additional_tags)

    @abstractmethod
    async def do_query(self) -> List[E]:
        pass

    @abstractmethod
    async def has_next(self) -> bool:
        pass

    async def next_page(self) -> List[E]:
        start = time.time()
        try:
            records = await self.do_query()
        except Exception as e:
            await self._stats_incr(
                "payment-etl.extract.failed.count",
                additional_tags={"exec_name": e.__class__.__name__},
            )
            raise
        self._stats_incr("payment-etl.extract.success.count")
        self._stats_gauge("payment-etl.extract.success.batch.size", len(records))
        self._stats_timing("payment-etl.extract.latency", time.time() - start)
        return records


class TransformAndLoadOne(Generic[E], StatsAndLogAware, ABC):

    record: E

    def __init__(
        self,
        statsd: DoorStatsProxyMultiServer,
        record: E,
        additional_tags: Optional[Dict[str, str]] = None,
    ):
        super().__init__(statsd=statsd, additional_tags=additional_tags)
        self.record = record

    @abstractmethod
    async def transform_and_load(self, record: E):
        pass

    @abstractmethod
    async def filter(self) -> Optional[E]:
        pass

    async def execute(self):
        start = time.time()

        try:
            filtered_result = await self.filter()
            if not filtered_result:
                self._stats_incr(f"payment-etl.transform-load.skipped.count")
            else:
                await self.transform_and_load(filtered_result)
        except Exception as e:
            self.log.exception("failed to transform and load data")
            self._stats_incr(
                "payment-etl.transform-load.failed.count",
                additional_tags={"exec_name": e.__class__.__name__},
            )
            self._stats_timing(
                f"payment-etl.transform-load.latency",
                time.time() - start,
                additional_tags={"status": "failed"},
            )
        else:
            self._stats_incr("payment-etl.transform-load.success.count")
            self._stats_timing(
                f"payment-etl.transform-load.latency",
                time.time() - start,
                additional_tags={"status": "success"},
            )
