import pytest

from typing import List
from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.utils.pool import ThreadPoolHelper
from app.commons.utils.testing import Stat
from app.commons.providers.stripe import stripe_http_client
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeClient, StripeAsyncClient


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
    def stripe_async_client(self, request, stripe_api, app_config: AppConfig):
        stripe_api.enable_mock()

        stripe_client = StripeClient(
            settings_list=[
                models.StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ],
            http_client=TimedRequestsClient(),
        )

        stripe_thread_pool = ThreadPoolHelper(
            max_workers=app_config.STRIPE_MAX_WORKERS, prefix="stripe"
        )

        stripe_async_client = StripeAsyncClient(
            executor_pool=stripe_thread_pool, stripe_client=stripe_client
        )

        yield stripe_async_client
        stripe_thread_pool.shutdown()

    async def test_customer(
        self, stripe_async_client: StripeAsyncClient, get_mock_statsd_events
    ):

        customer_id = await stripe_async_client.create_customer(
            country=models.CountryCode.US,
            request=models.StripeCreateCustomerRequest(
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
            "status_code": "200",
            "request_status": "success",
        }
