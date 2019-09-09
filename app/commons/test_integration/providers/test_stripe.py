import pytest

from typing import List
from app.commons.utils.testing import Stat
from app.commons.providers.stripe import stripe_http_client
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeClientPool


@pytest.fixture(autouse=True)
def setup(service_statsd_client):
    # ensure that we mock the statsd service client
    yield
    # reset the stripe http client
    stripe_http_client.set_default_http_client(None)


class TestStripePoolStats:
    pytestmark = [
        # use an event loop for all these tests
        pytest.mark.asyncio,
        pytest.mark.integration,
    ]

    @pytest.fixture
    def stripe_pool(self, request, stripe_api):
        stripe_api.enable_mock()

        pool = StripeClientPool(
            max_workers=5,
            settings_list=[
                models.StripeClientSettings(
                    api_key="sk_test_4eC39HqLyjWDarjtT1zdp7dc", country="US"
                )
            ],
        )
        yield pool
        pool.shutdown()

    async def test_customer(
        self, stripe_pool: StripeClientPool, get_mock_statsd_events
    ):

        customer_id = await stripe_pool.create_customer(
            country=models.CountryCode.US,
            request=models.CreateCustomer(
                email="test@user.com", description="customer name", country="US"
            ),
        )
        assert customer_id

        events: List[Stat] = get_mock_statsd_events()
        assert len(events) == 1
        event = events[0]
        assert event.stat_name == "dd.pay.payment-service.io.stripe-lib.latency"
        assert event.tags == {
            "provider_name": "stripe",
            "country": "US",
            "resource": "customer",
            "action": "create",
            # "status_code": "",  # not yet implemented
        }
