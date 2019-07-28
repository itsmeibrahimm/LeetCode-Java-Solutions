import pytest
import stripe
from app.commons.providers.stripe import (
    StripeClient,
    StripeTestClient,
    StripePoolHelper,
)
from app.commons.providers import stripe_models as models


@pytest.fixture
def stripe_mock():
    """
    for mock stripe, change the URL
    """
    api_url = stripe.api_base
    stripe.api_base = "http://localhost:12111"
    yield
    stripe.api_base = api_url


pytestmark = [
    pytest.mark.parametrize(
        "mode",
        [
            # execute these tests using the mock stripe
            pytest.param("mock", marks=[pytest.mark.usefixtures("stripe_mock")]),
            # and again using the real stripe (external provider)
            pytest.param("external", marks=[pytest.mark.external]),
        ],
    )
]


class TestStripeClient:
    @pytest.fixture
    def stripe(self):
        return StripeClient("sk_test_4eC39HqLyjWDarjtT1zdp7dc", "US")

    @pytest.fixture
    def stripe_test(self):
        return StripeTestClient("sk_test_4eC39HqLyjWDarjtT1zdp7dc", "US")

    @pytest.mark.skip(reason="requires connected account key")
    def test_token(self, mode: str, stripe: StripeClient):
        token_id = stripe.create_connected_account_token(
            models.CreateConnectedAccountToken(
                card="card_1F0HgE2eZvKYlo2CpI7aVFkd",
                stripe_account="acct_1032D82eZvKYlo2C",
                country="US",
                customer="cus_FVIHDAyh5HbO5L",
            )
        )
        assert token_id

    def test_customer(self, mode: str, stripe: StripeClient):
        customer_id = stripe.create_customer(
            models.CreateCustomer(
                email="test@user.com", description="customer name", country="US"
            )
        )
        assert customer_id


class TestStripePool:
    pytestmark = [
        # use an event loop for all these tests
        pytest.mark.asyncio
    ]

    @pytest.fixture
    def stripe_pool(self):
        return StripePoolHelper(
            max_workers=5, api_key="sk_test_4eC39HqLyjWDarjtT1zdp7dc", country="US"
        )

    @pytest.mark.skip(reason="requires connected account key")
    async def test_token(self, mode: str, stripe_pool: StripePoolHelper):
        token_id = await stripe_pool.create_connected_account_token(
            models.CreateConnectedAccountToken(
                card="card_1F0HgE2eZvKYlo2CpI7aVFkd",
                stripe_account="acct_1032D82eZvKYlo2C",
                country="US",
                customer="cus_FVIHDAyh5HbO5L",
            )
        )
        assert token_id

    async def test_customer(self, mode: str, stripe_pool: StripePoolHelper):
        customer_id = await stripe_pool.create_customer(
            models.CreateCustomer(
                email="test@user.com", description="customer name", country="US"
            )
        )
        assert customer_id
