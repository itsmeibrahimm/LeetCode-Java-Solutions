import asyncio
from typing import List, Optional
from app.commons.instrumentation.types import MonitoringProcessor, Logger, StatsClient


class MonitoringManager:
    processors: List[MonitoringProcessor] = []
    logger: Logger
    stats_client: StatsClient
    _task: Optional[asyncio.Task] = None

    def __init__(
        self,
        *,
        stats_client: StatsClient,
        logger: Logger,
        processors: Optional[List[MonitoringProcessor]] = None,
    ):
        """
        registry of application-level monitors. these will be scheduled periodically

        Keyword Arguments:
            processors {Optional[List[MonitoringProcessor]]} -- [description] (default: {None})
        """
        self.stats_client = stats_client
        self.logger = logger
        if processors:
            self.processors = processors

    async def _monitoring_loop(self, interval_secs: float, call_immediately: bool):
        if not call_immediately:
            # sleep once before the first iteration
            await asyncio.sleep(interval_secs)

        while True:
            for processor in self.processors:
                try:
                    processor(self.stats_client, self.logger)
                except Exception:
                    self.logger.warn(
                        "error processing monitor %s", processor.__name__, exc_info=True
                    )
            await asyncio.sleep(interval_secs)

    def add(self, processor: MonitoringProcessor):
        self.processors.append(processor)

    def start(
        self,
        interval_secs: float = 30,
        *,
        call_immediately=False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        schedule the monitoring loop for execution
        """
        if self._task and not self._task.done():
            # task already started
            return False

        if not loop:
            loop = asyncio.get_event_loop()
        self._task = loop.create_task(
            self._monitoring_loop(interval_secs, call_immediately=call_immediately)
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
