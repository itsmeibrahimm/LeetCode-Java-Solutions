import pytest
import stripe.error

from typing import List
from app.commons import tracing
from app.commons.utils.testing import Stat
from app.commons.providers.stripe import stripe_http_client


@pytest.fixture(autouse=True)
def setup(service_statsd_client):
    # ensure that we mock the statsd service client
    ...


def test_stripe_http_client(get_mock_statsd_events):
    client = stripe_http_client.TimedRequestsClient()
    with pytest.raises(stripe.error.StripeError), tracing.breadcrumb_as(
        tracing.Breadcrumb(application_name="myapp", country="US", status_code="500")
    ):
        client.request("GET", "http://localhost", {})

    events: List[Stat] = get_mock_statsd_events()
    assert len(events) == 1
    event = events[0]
    assert event.stat_name == "dd.pay.payment-service.io.stripe-lib.latency"
    assert event.tags == {
        "application_name": "myapp",
        "country": "US",
        "status_code": "500",
    }
