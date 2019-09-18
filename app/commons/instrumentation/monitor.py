import asyncio
from typing import Dict, List, Optional, Set
from app.commons.instrumentation.types import MonitoringProcessor, Logger, StatsClient


class MonitoringManager:
    """
    manage application-level asyncio monitors

    these are intended to be scheduled and run in the event loop
    """

    loop: Optional[asyncio.AbstractEventLoop] = None
    processors: Dict[float, "MonitoringLoop"]
    logger: Logger
    stats_client: StatsClient
    default_interval_secs: float
    started: bool = False

    def __init__(
        self,
        *,
        stats_client: StatsClient,
        logger: Logger,
        default_processors: Optional[List[MonitoringProcessor]] = None,
        default_interval_secs: float = 30,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.stats_client = stats_client
        self.logger = logger
        self.processors = {}
        if default_interval_secs <= 0:
            raise ValueError("default_interval_secs must be greater than 0")
        self.default_interval_secs = default_interval_secs
        self.loop = loop
        if default_processors is not None:
            for proc in default_processors:
                self.add(proc, interval_secs=self.default_interval_secs)

    def add(
        self, processor: MonitoringProcessor, *, interval_secs: Optional[float] = None
    ):
        interval_secs = interval_secs or self.default_interval_secs
        if interval_secs <= 0:
            raise ValueError("interval_secs must be greater than 0")
        manager = self.processors.get(interval_secs, None)
        if not manager:
            self.processors[interval_secs] = manager = MonitoringLoop(
                interval_secs=interval_secs,
                stats_client=self.stats_client,
                logger=self.logger,
                loop=self.loop,
            )

            # start the manager if we've already started the rest of them
            if self.started:
                manager.start(call_immediately=True)
        manager.add(processor)

    def start(self, *, call_immediately=False):
        if self.started:
            return False
        self.started = True

        for manager in self.processors.values():
            manager.start(call_immediately=call_immediately)

        return True

    def stop(self):
        if not self.started:
            return False
        self.started = False

        for manager in self.processors.values():
            manager.stop()

        return True


class MonitoringLoop:
    interval_secs: float
    processors: Set[MonitoringProcessor]
    logger: Logger
    stats_client: StatsClient
    loop: asyncio.AbstractEventLoop
    _task: Optional[asyncio.Task] = None

    def __init__(
        self,
        *,
        interval_secs: float,
        stats_client: StatsClient,
        logger: Logger,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        processors: Optional[List[MonitoringProcessor]] = None,
    ):
        """
        registry of application-level monitors. these will be scheduled periodically

        Keyword Arguments:
            processors {Optional[List[MonitoringProcessor]]} -- [description] (default: {None})
        """
        self.interval_secs = interval_secs
        self.stats_client = stats_client
        self.logger = logger
        self.loop = loop or asyncio.get_event_loop()
        if processors:
            self.processors = set(processors)
        else:
            self.processors = set()

    async def _monitoring_loop(self, call_immediately: bool):
        if not call_immediately:
            # sleep once before the first iteration
            await asyncio.sleep(self.interval_secs)

        while True:
            for processor in self.processors:
                try:
                    processor(self.stats_client, self.logger)
                except Exception:
                    self.logger.warn(
                        "error processing monitor %s", processor.__name__, exc_info=True
                    )
            await asyncio.sleep(self.interval_secs)

    def add(self, processor: MonitoringProcessor):
        self.processors.add(processor)

    def start(self, *, call_immediately=False):
        """
        schedule the monitoring loop for execution
        """
        if self._task and not self._task.done():
            # task already started
            return False

        self._task = self.loop.create_task(
            self._monitoring_loop(call_immediately=call_immediately)
        )
        return True

    def stop(self):
        """
        stop the monitoring loop
        """
        if not self._task or self._task.done():
            # task not started or already done
            return False
        self._task.cancel()
        self._task = None
        return True
