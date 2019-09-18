import functools
from typing import Any, Callable, List, Dict, Optional

import structlog
from doordash_python_stats import ddstats

from app.commons import tracing
from app.commons.context.logger import root_logger as default_logger
from app.commons.stats import get_service_stats_client, get_request_logger
from app.commons.tracing import Processor, TManager, Unspecified


def stat_func_timing(tracker: "FuncTimingManager", timer: "FuncTimer"):
    log: structlog.stdlib.BoundLogger = get_request_logger(default=default_logger)
    tags = {"func": timer.func_name}
    stats: ddstats.DoorStatsProxyMultiServer = get_service_stats_client()
    # Measure the duration of this func
    duration_stat_name = f"funcs.{tracker.stat_name}.duration"
    stats.timing(duration_stat_name, timer.delta_ms, tags=tags)
    log.debug(
        "duration stat", duration_stat_name=duration_stat_name, delta_ms=timer.delta_ms
    )


class FuncTimer(tracing.BaseTimer):
    def __init__(self, func_name: str):
        super().__init__()
        self.func_name = func_name


class FuncTimingManager(tracing.TimingManager[FuncTimer]):
    processors = [stat_func_timing]

    def __init__(
        self: TManager,
        *,
        func_name: str,
        stat_name: str,
        send=True,
        rate=1,
        processors: Optional[List[Processor]] = None,
        only_trackable=False,
    ):
        super().__init__(
            send=send, rate=rate, processors=processors, only_trackable=only_trackable
        )
        self.func_name = func_name
        self.stat_name = stat_name

    def create_tracker(
        self,
        obj=Unspecified,
        *,
        func: Callable,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> FuncTimer:
        return FuncTimer(func_name=self.func_name)


def track_func(func=None, stat_name: str = None):
    if func is None:
        return functools.partial(track_func, stat_prefix=stat_name)
    stat_name = stat_name or func.__name__
    func_name = func.__name__

    return FuncTimingManager(func_name=func_name, stat_name=stat_name)(func)
