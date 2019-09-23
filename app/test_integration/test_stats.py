from typing import Dict, List

import pytest
from starlette.testclient import TestClient
from app.commons.utils.testing import Stat


@pytest.mark.skip(reason="On CI, there are other clients hitting this endpoint")
def test_request_stats(client: TestClient, get_mock_statsd_events):
    client.get("/health")

    events: List[Stat] = get_mock_statsd_events()
    stat_names: Dict[str, Stat] = {event.stat_name: event for event in events}

    response_name = "dd.response.2XX"
    assert response_name in stat_names
    response_stat = stat_names[response_name]
    assert response_stat.tags["hostname"]
    assert response_stat.tags["method"] == "GET"
    assert response_stat.tags["status_code"] == "200"

    latency_name = "dd.response.latency"
    assert latency_name in stat_names
    latency_stat = stat_names[latency_name]
    assert latency_stat.tags["hostname"]
    assert latency_stat.tags["method"] == "GET"
    assert latency_stat.tags["status_code"] == "200"
