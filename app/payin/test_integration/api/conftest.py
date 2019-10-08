import pytest

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.providers.stripe import stripe_models
from app.commons.providers.stripe.stripe_models import Customer
from app.commons.types import CountryCode


@pytest.fixture
def stripe_client(stripe_api, app_config: AppConfig):
    stripe_api.enable_outbound()

    return StripeTestClient(
        [
            stripe_models.StripeClientSettings(
                api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
            )
        ]
    )


@pytest.fixture
def stripe_customer(stripe_client: StripeTestClient) -> Customer:
    request = stripe_models.StripeCreateCustomerRequest(
        email="test@dd.com", description="test account"
    )

    return stripe_client.create_customer(request=request, country=CountryCode.US)
