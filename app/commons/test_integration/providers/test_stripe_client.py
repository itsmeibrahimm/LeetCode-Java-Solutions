import pytest
from stripe.error import InvalidRequestError

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe.stripe_client import (
    StripeClient,
    StripeTestClient,
    StripeAsyncClient,
)
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.test_integration.constants import DEBIT_CARD_TOKEN, DEBIT_CARD_NUMBER
from app.commons.test_integration.utils import (
    prepare_and_validate_stripe_account,
    prepare_and_validate_stripe_account_token,
)
from app.commons.utils.pool import ThreadPoolHelper
from app.commons.providers.stripe.stripe_models import (
    CreateCardToken,
    CreateExternalAccountRequest,
    CreateCardTokenRequest,
)
from app.commons.types import Currency, CountryCode
from app.payout.types import PayoutExternalAccountType

pytestmark = [
    # mark all these tests as stripe tests
    pytest.mark.stripe,
    # allow all tests to be run against the stripe mock (as integration tests)
    # and against the real stripe (as external tests)
    pytest.mark.parametrize(
        "mode",
        [
            # the `mock` tests are integration tests against the stripe-mock
            pytest.param("mock", marks=[pytest.mark.integration]),
            # the `external` tests are integration tests against the real stripe test account
            pytest.param("external", marks=[pytest.mark.external]),
        ],
    ),
]


class TestStripeClient:
    @pytest.fixture
    def stripe(self, request, stripe_api, app_config: AppConfig):
        # allow external tests to directly call stripe
        if "external" in request.keywords:
            stripe_api.enable_outbound()
        # allow integration tests to call the stripe mock
        elif "integration" in request.keywords:
            stripe_api.enable_mock()

        return StripeClient(
            [
                models.StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ]
        )

    @pytest.fixture
    def stripe_test(self, request, stripe_api, app_config: AppConfig):
        # allow external tests to directly call stripe
        if "external" in request.keywords:
            stripe_api.enable_outbound()
        # allow integration tests to call the stripe mock
        elif "integration" in request.keywords:
            stripe_api.enable_mock()

        return StripeTestClient(
            [
                models.StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ]
        )

    def test_customer(self, mode: str, stripe: StripeClient):
        customer_id = stripe.create_customer(
            country=models.CountryCode.US,
            request=models.StripeCreateCustomerRequest(
                email="test@user.com", description="customer name", country="US"
            ),
        )
        assert customer_id

        customer = stripe.retrieve_customer(
            country=models.CountryCode.US,
            request=models.StripeRetrieveCustomerRequest(id=customer_id),
        )
        assert customer

    @pytest.mark.skip(
        "requires to create the needed resource first in case it becomes flaky"
    )
    def test_create_transfer(self, mode: str, stripe: StripeClient):
        transfer = stripe.create_transfer(
            country=models.CountryCode.US,
            currency=models.Currency(Currency.USD.value),
            destination=models.Destination("acct_1A29cNCyrpkWaAxi"),
            amount=models.Amount(200),
            request=models.StripeCreateTransferRequest(description="test description"),
        )
        assert transfer.id

    @pytest.mark.skip(
        "requires to create the needed resource first in case it becomes flaky"
    )
    def test_create_payout(self, mode: str, stripe: StripeClient):
        payout = stripe.create_payout(
            country=models.CountryCode.US,
            currency=models.Currency(Currency.USD.value),
            amount=models.Amount(2),
            stripe_account=models.StripeAccountId("acct_1FGdyOBOQHMRR5FG"),
            request=models.StripeCreatePayoutRequest(method="standard"),
        )
        assert payout.id

    @pytest.mark.skip(
        "requires to create the needed resource first in case it becomes flaky"
    )
    def test_create_and_retrieve_payout(self, mode: str, stripe: StripeClient):
        payout = stripe.create_payout(
            country=models.CountryCode.US,
            currency=models.Currency(Currency.USD.value),
            amount=models.Amount(2),
            stripe_account=models.StripeAccountId("acct_1FGdyOBOQHMRR5FG"),
            request=models.StripeCreatePayoutRequest(method="standard"),
        )
        assert payout.id

        retrieved_payout = stripe.retrieve_payout(
            country=models.CountryCode.US,
            request=models.StripeRetrievePayoutRequest(
                stripe_account="acct_1FGdyOBOQHMRR5FG", id=payout.id
            ),
        )
        assert retrieved_payout.id == payout.id

    @pytest.mark.skip(
        "requires to create the needed resource first in case it becomes flaky"
    )
    def test_retrieve_payout_not_found(self, mode: str, stripe: StripeClient):
        if mode == "mock":
            pytest.skip()

        with pytest.raises(InvalidRequestError):
            stripe.retrieve_payout(
                country=models.CountryCode.US,
                request=models.RetrievePayout(
                    stripe_account="acct_1FGdyOBOQHMRR5FG", id="invalid_payout_id"
                ),
            )

    @pytest.mark.skip(
        "requires to create the needed resource first in case it becomes flaky"
    )
    def test_create_and_cancel_payout(self, mode: str, stripe: StripeClient):
        payout = stripe.create_payout(
            country=models.CountryCode.US,
            currency=models.Currency(Currency.USD.value),
            amount=models.Amount(2),
            stripe_account=models.StripeAccountId("acct_1FGdyOBOQHMRR5FG"),
            request=models.StripeCreatePayoutRequest(method="standard"),
        )
        assert payout.id

        try:
            payout_cancelled = stripe.cancel_payout(
                country=models.CountryCode.US,
                request=models.StripeCancelPayoutRequest(
                    stripe_account="acct_1FGdyOBOQHMRR5FG", sid=payout.id
                ),
            )

            # For testing against stripe_mock service locally, we should be able to cancel the payout
            assert payout_cancelled.id == payout.id
        except InvalidRequestError as e:
            # For testing against real stripe service with test api_key, we should get the InvalidRequestError
            assert e.http_status == 400
            assert (
                e.json_body["error"]["message"]
                == "Payouts can only be canceled while they are pending."
            )

    @pytest.mark.skip(
        "requires to create the needed resource first in case it becomes flaky"
    )
    def test_retrieve_balance(self, mode: str, stripe: StripeClient):
        balance = stripe.retrieve_balance(
            country=models.CountryCode.US,
            stripe_account=models.StripeAccountId("acct_1A29cNCyrpkWaAxi"),
        )
        assert balance

    # this test doesn't work as expected for stripe mock
    # it should returns an account token but returns a card token
    # works fine for external
    def test_create_account_token(self, mode: str, stripe: StripeClient):
        if mode == "mock":
            pytest.skip()

        prepare_and_validate_stripe_account_token(stripe)

    def test_create_account(self, mode: str, stripe: StripeClient):
        # should use create_account_token to generate an account token
        # stripe mock doesn't work as expected by returning a card token instead of account token
        # test_account_token = "ct_Fny00gsFtsBBaU"

        if mode == "mock":
            pytest.skip()
        prepare_and_validate_stripe_account(stripe)

    def test_create_card_token(self, mode: str, stripe_test: StripeTestClient):
        # stripe mock always create a token for bank account which is not right for this use
        if mode == "mock":
            pytest.skip()
        card_token = stripe_test.create_card_token(
            request=CreateCardTokenRequest(
                country=CountryCode.US,
                card=CreateCardToken(
                    number=DEBIT_CARD_NUMBER,
                    exp_month=10,
                    exp_year=2022,
                    cvc="123",
                    currency="usd",
                ),
            ),
            idempotency_key=None,
        )
        assert card_token
        assert card_token.id.startswith("tok_")
        assert card_token.type == "card"

    def test_create_external_account_card(
        self, mode: str, stripe_test: StripeTestClient
    ):
        if mode == "mock":
            pytest.skip()
        account = prepare_and_validate_stripe_account(stripe_test)
        card = stripe_test.create_external_account_card(
            request=CreateExternalAccountRequest(
                country=CountryCode.US,
                type=PayoutExternalAccountType.CARD.value,
                stripe_account_id=account.id,
                external_account_token=DEBIT_CARD_TOKEN,
            )
        )
        assert card
        assert card.object == "card"
        assert card.id.startswith("card_")


class TestStripePool:
    pytestmark = [
        # use an event loop for all these tests
        pytest.mark.asyncio
    ]

    @pytest.fixture
    def stripe_async_client(self, request, stripe_api, app_config: AppConfig):
        # allow external tests to directly call stripe
        if "external" in request.keywords:
            stripe_api.enable_outbound()
        # allow integration tests to call the stripe mock
        elif "integration" in request.keywords:
            stripe_api.enable_mock()

        stripe_client = StripeClient(
            settings_list=[
                # TODO: add CA/AU
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

    async def test_customer(self, mode: str, stripe_async_client: StripeAsyncClient):
        customer_id = await stripe_async_client.create_customer(
            country=models.CountryCode.US,
            request=models.StripeCreateCustomerRequest(
                email="test@user.com", description="customer name", country="US"
            ),
        )
        assert customer_id
