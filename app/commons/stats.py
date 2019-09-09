import functools
import platform
import structlog

from contextvars import ContextVar
from typing import Any, Dict, Optional

from app.commons.context.logger import root_logger
from app.commons.tracing import NotSpecified, contextvar_as, get_contextvar
from app.commons.config.app_config import StatsDConfig
from doordash_python_stats.ddstats import DoorStatsProxyMultiServer, doorstats_global


SERVICE_STATS_CLIENT: ContextVar[DoorStatsProxyMultiServer] = ContextVar(
    "SERVICE_STATS_CLIENT", default=doorstats_global
)
# this should only be used when the module does not have access to the request context
# ie. resources that are instantiated at the application level
REQUEST_LOGGER: ContextVar[structlog.stdlib.BoundLogger] = ContextVar(
    "REQUEST_LOGGER", default=root_logger
)

set_service_stats_client = functools.partial(contextvar_as, SERVICE_STATS_CLIENT)
set_request_logger = functools.partial(contextvar_as, REQUEST_LOGGER)


def get_service_stats_client(default=NotSpecified) -> DoorStatsProxyMultiServer:
    return get_contextvar(SERVICE_STATS_CLIENT, default=default)


def get_request_logger(default=NotSpecified) -> structlog.stdlib.BoundLogger:
    return get_contextvar(REQUEST_LOGGER, default=default)


def init_statsd(
    prefix: str,
    *,
    proxy: DoorStatsProxyMultiServer = None,
    host: str,
    fixed_tags: Optional[Dict[str, str]] = None,
):
    """
    Initialize a StatsD client
    """
    proxy = proxy or DoorStatsProxyMultiServer()
    proxy.initialize(host=host, prefix=prefix, fixed_tags=fixed_tags)
    return proxy


def init_statsd_from_config(
    host: str,
    config: StatsDConfig,
    *,
    proxy: DoorStatsProxyMultiServer = None,
    tags: Optional[Dict[str, str]] = None,
    additional_tags: Optional[Dict[str, str]] = None,
):
    combined_tags = tags or dict(**config.TAGS)
    if additional_tags:
        combined_tags.update(additional_tags)
    return init_statsd(config.PREFIX, proxy=proxy, host=host, fixed_tags=combined_tags)


def init_global_statsd(prefix: str, *, host: str, fixed_tags: Dict[str, Any] = {}):
    fixed_tags = {"hostname": platform.node(), **fixed_tags}
    return init_statsd(prefix, proxy=doorstats_global, host=host, fixed_tags=fixed_tags)
