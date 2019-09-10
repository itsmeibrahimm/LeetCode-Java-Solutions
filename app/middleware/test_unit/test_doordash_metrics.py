from pytest_mock import MockFixture

from typing import List
from app.commons.utils.testing import Stat
from app.commons.config.app_config import StatsDConfig
from app.middleware.doordash_metrics import ServiceMetricsMiddleware, normalize_path


def test_normalize_path():
    assert normalize_path("/api/v1/{id}") == "|api|v1|id"


class TestServiceMetricsMiddleware:
    def test_middleware(self, get_mock_statsd_events, mocker: MockFixture):
        app = mocker.Mock()  # typing: disable
        config = StatsDConfig()
        middleware = ServiceMetricsMiddleware(
            app=app, application_name="this-app-v1", host="localhost", config=config
        )
        middleware.statsd_client.incr("test.stat")

        events: List[Stat] = get_mock_statsd_events()
        assert len(events) == 1
        event = events[0]
        assert event.stat_name == "dd.pay.payment-service.test.stat"

        tags = event.tags.copy()
        container = tags.pop("container", None)
        assert container is not None, "container hostname is set"
        assert tags == dict(), "no additional tags are present"

    def test_additional_tags(self, get_mock_statsd_events, mocker: MockFixture):
        app = mocker.Mock()  # typing: disable
        config = StatsDConfig()
        middleware = ServiceMetricsMiddleware(
            app=app,
            application_name="this-app-v1",
            host="localhost",
            config=config,
            additional_tags={"my": "tag"},
        )
        middleware.statsd_client.incr("test.stat")

        events: List[Stat] = get_mock_statsd_events()
        assert len(events) == 1
        event = events[0]
        assert event.stat_name == "dd.pay.payment-service.test.stat"

        tags = event.tags.copy()
        container = tags.pop("container", None)
        assert container is not None, "container hostname is set"
        assert tags == {"my": "tag"}, "additional tags are configured"
