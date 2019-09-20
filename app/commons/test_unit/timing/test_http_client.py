import pytest
import requests
from typing import List
from app.commons.timing import http_client

from app.commons.utils.testing import Stat


@http_client.track_stripe_http_client(stat_name="io.stripe-client.latency")
class StripeClient:
    def do_success(self):
        response = requests.Response()
        response.status_code = 200
        return response

    def do_forbidden(self):
        response = requests.Response()
        response.status_code = 401
        return response

    def do_server_error(self):
        response = requests.Response()
        response.status_code = 500
        return response

    def do_timeout(self):
        raise requests.Timeout()

    def do_error(self):
        raise RuntimeError()


def test_success(global_statsd_client, get_mock_statsd_events):
    client = StripeClient()
    client.do_success()

    prefix = "dd.pay.payment-service"

    events: List[Stat] = get_mock_statsd_events()
    assert len(events) == 1
    stat = events[0]
    assert stat.stat_name == f"{prefix}.io.stripe-client.latency"
    assert stat.tags["request_status"] == "success"
    assert stat.tags["status_code"] == "200"


def test_client_error(global_statsd_client, get_mock_statsd_events):
    client = StripeClient()
    client.do_forbidden()

    prefix = "dd.pay.payment-service"

    events: List[Stat] = get_mock_statsd_events()
    assert len(events) == 1
    stat = events[0]
    assert stat.stat_name == f"{prefix}.io.stripe-client.latency"
    assert stat.tags["request_status"] == "client_error"
    assert stat.tags["status_code"] == "401"


def test_server_error(global_statsd_client, get_mock_statsd_events):
    client = StripeClient()
    client.do_server_error()

    prefix = "dd.pay.payment-service"

    events: List[Stat] = get_mock_statsd_events()
    assert len(events) == 1
    stat = events[0]
    assert stat.stat_name == f"{prefix}.io.stripe-client.latency"
    assert stat.tags["request_status"] == "server_error"
    assert stat.tags["status_code"] == "500"


def test_timeout(global_statsd_client, get_mock_statsd_events):
    client = StripeClient()
    with pytest.raises(requests.Timeout):
        client.do_timeout()

    prefix = "dd.pay.payment-service"

    events: List[Stat] = get_mock_statsd_events()
    assert len(events) == 1
    stat = events[0]
    assert stat.stat_name == f"{prefix}.io.stripe-client.latency"
    assert stat.tags["request_status"] == "timeout"


def test_error(global_statsd_client, get_mock_statsd_events):
    client = StripeClient()
    with pytest.raises(RuntimeError):
        client.do_error()

    prefix = "dd.pay.payment-service"

    events: List[Stat] = get_mock_statsd_events()
    assert len(events) == 1
    stat = events[0]
    assert stat.stat_name == f"{prefix}.io.stripe-client.latency"
    assert stat.tags["request_status"] == "exception"
