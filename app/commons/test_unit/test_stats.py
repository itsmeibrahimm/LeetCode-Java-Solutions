import pytest
from doordash_python_stats.ddstats import DoorStatsProxyMultiServer, doorstats_global
from app.commons.context.logger import root_logger, get_logger
from app.commons.stats import (
    get_service_stats_client,
    set_service_stats_client,
    get_request_logger,
    set_request_logger,
)


log = get_logger(__name__)


@pytest.fixture
def statsd_client():
    return DoorStatsProxyMultiServer()


def test_get_service_stats_client(statsd_client: DoorStatsProxyMultiServer):
    assert get_service_stats_client() is doorstats_global, "fallback to global stats"
    assert (
        get_service_stats_client(statsd_client) is statsd_client
    ), "specifying default"


def test_set_service_stats_client(statsd_client: DoorStatsProxyMultiServer):
    assert get_service_stats_client() is doorstats_global
    with set_service_stats_client(statsd_client):
        assert get_service_stats_client() is statsd_client
    assert get_service_stats_client() is doorstats_global


def test_get_request_logger():
    assert get_request_logger() is root_logger, "fallback to root logger"
    assert get_request_logger(log) is log, "specifying default"


def test_set_request_logger():
    assert get_request_logger() is root_logger
    with set_request_logger(log):
        assert get_request_logger() is log
    assert get_request_logger() is root_logger
