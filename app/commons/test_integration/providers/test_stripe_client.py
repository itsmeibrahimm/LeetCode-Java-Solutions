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
from app.commons.utils.pool import ThreadPoolHelper
from app.commons.providers.stripe.stripe_models import (
    DateOfBirth,
    CreateAccountRequest,
    Address,
    CreateAccountTokenRequest,
    Individual,
    CreateAccountTokenMetaDataRequest,
)
from app.commons.types import Currency, CountryCode

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

        # generate account token
        data = CreateAccountTokenMetaDataRequest(
            business_type="individual",
            individual=Individual(
                first_name="Test",
                last_name="Payment",
                dob=DateOfBirth(day=1, month=1, year=1990),
                address=Address(
                    city="Mountain View",
                    country=CountryCode.US.value,
                    line1="123 Castro St",
                    line2="",
                    postal_code="94041",
                    state="CA",
                ),
                ssn_last_4="1234",
            ),
            tos_shown_and_accepted=True,
        )
        account_token = stripe.create_account_token(
            request=CreateAccountTokenRequest(account=data, country=CountryCode.US)
        )
        assert account_token

    def test_create_account(self, mode: str, stripe: StripeClient):
        # should use create_account_token to generate an account token
        # stripe mock doesn't work as expected by returning a card token instead of account token
        # test_account_token = "ct_Fny00gsFtsBBaU"

        if mode == "mock":
            pytest.skip()
        data = CreateAccountTokenMetaDataRequest(
            business_type="individual",
            individual=Individual(
                first_name="Test",
                last_name="Payment",
                dob=DateOfBirth(day=1, month=1, year=1990),
                address=Address(
                    city="Mountain View",
                    country=CountryCode.US.value,
                    line1="123 Castro St",
                    line2="",
                    postal_code="94041",
                    state="CA",
                ),
                ssn_last_4="1234",
            ),
            tos_shown_and_accepted=True,
        )
        account_token = stripe.create_account_token(
            request=CreateAccountTokenRequest(account=data, country=CountryCode.US)
        )
        assert account_token

        account = stripe.create_stripe_account(
            request=CreateAccountRequest(
                country=CountryCode.US,
                type="custom",
                account_token=account_token.id,
                requested_capabilities=["legacy_payments"],
            )
        )
        assert account
        assert account.id.startswith("acct_")


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
