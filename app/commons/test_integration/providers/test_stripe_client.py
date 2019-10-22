import pytest
from stripe.error import InvalidRequestError

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.constants import STRIPE_PLATFORM_ACCOUNT_IDS
from app.commons.providers.stripe.stripe_client import (
    StripeAsyncClient,
    StripeClient,
    StripeTestClient,
)
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import (
    ClonePaymentMethodRequest,
    CreateAccountTokenMetaDataRequest,
    PaymentMethodId,
    StripeAttachPaymentMethodRequest,
    StripeCreateCardRequest,
    StripeCreateCustomerRequest,
    TokenId,
    RetrieveAccountRequest,
)
from app.commons.test_integration.constants import VISA_DEBIT_CARD_TOKEN
from app.commons.test_integration.utils import (
    prepare_and_validate_stripe_account,
    prepare_and_validate_stripe_account_token,
)
from app.commons.types import CountryCode, Currency
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.models import PayoutExternalAccountType

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
                    api_key=app_config.STRIPE_US_SECRET_KEY.value,
                    country=CountryCode.US,
                ),
                models.StripeClientSettings(
                    api_key=app_config.STRIPE_CA_SECRET_KEY.value,
                    country=CountryCode.CA,
                ),
                models.StripeClientSettings(
                    api_key=app_config.STRIPE_AU_SECRET_KEY.value,
                    country=CountryCode.AU,
                ),
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
                    api_key=app_config.STRIPE_US_SECRET_KEY.value,
                    country=CountryCode.US,
                )
            ]
        )

    @pytest.mark.vcr()
    def test_customer(self, mode: str, stripe: StripeClient):
        if mode == "mock":
            pytest.skip()
        customer = stripe.create_customer(
            country=models.CountryCode.US,
            request=models.StripeCreateCustomerRequest(
                email="test@user.com", description="customer name"
            ),
        )
        assert customer

        customer = stripe.retrieve_customer(
            country=models.CountryCode.US,
            request=models.StripeRetrieveCustomerRequest(id=customer.id),
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

    def test_update_account(self, mode: str, stripe: StripeClient):
        # should use create_account_token to generate an account token
        # stripe mock doesn't work as expected by returning a card token instead of account token
        # test_account_token = "ct_Fny00gsFtsBBaU"

        if mode == "mock":
            pytest.skip()
        create_account_token_data = CreateAccountTokenMetaDataRequest(
            business_type="individual",
            individual=models.Individual(
                first_name="Test",
                last_name="Payment",
                dob=models.DateOfBirth(day=1, month=1, year=1990),
                address=models.Address(
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
        account_token = prepare_and_validate_stripe_account_token(
            stripe_client=stripe, data=create_account_token_data
        )
        account = prepare_and_validate_stripe_account(stripe, account_token)
        assert account.individual.first_name == "Test"
        assert account.individual.last_name == "Payment"
        assert account.business_type == create_account_token_data.business_type

        first_name = "Frosty"
        last_name = "Fish"
        updated_create_account_token_data = CreateAccountTokenMetaDataRequest(
            business_type="individual",
            individual=models.Individual(
                first_name=first_name,
                last_name=last_name,
                dob=models.DateOfBirth(day=5, month=5, year=1991),
                address=models.Address(
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
        new_token = prepare_and_validate_stripe_account_token(
            stripe_client=stripe, data=updated_create_account_token_data
        )
        updated_account = stripe.update_account(
            request=models.UpdateAccountRequest(
                id=account.id, country=CountryCode.US, account_token=new_token.id
            )
        )
        assert updated_account
        assert updated_account.individual.first_name == first_name
        assert updated_account.individual.last_name == last_name
        assert updated_account.individual.dob.day == 5
        assert updated_account.individual.dob.month == 5
        assert updated_account.individual.dob.year == 1991
        assert updated_account.individual.first_name != account.individual.first_name
        assert updated_account.individual.last_name != account.individual.last_name
        assert updated_account.individual.dob.day != account.individual.dob.day
        assert updated_account.individual.dob.month != account.individual.dob.month
        assert updated_account.individual.dob.year != account.individual.dob.year

    @pytest.mark.vcr()
    def test_create_payment_method(self, mode: str, stripe: StripeClient):
        if mode == "mock":
            pytest.skip()

        stripe_customer = stripe.create_customer(
            request=StripeCreateCustomerRequest(
                email="hahn@doordash.com", description="Hello!"
            ),
            country=CountryCode.US,
        )
        stripe_payment_method = stripe.attach_payment_method(
            request=StripeAttachPaymentMethodRequest(
                payment_method="pm_card_visa", customer=stripe_customer.id
            ),
            country=CountryCode.US,
        )
        assert stripe_payment_method.customer == stripe_customer.id

    @pytest.mark.vcr()
    def test_clone_payment_method(self, mode: str, stripe: StripeClient):
        if mode == "mock":
            pytest.skip()

        stripe_customer = stripe.create_customer(
            request=StripeCreateCustomerRequest(
                email="hahn@doordash.com", description="Hello!"
            ),
            country=CountryCode.US,
        )
        stripe_payment_method = stripe.attach_payment_method(
            request=StripeAttachPaymentMethodRequest(
                payment_method="pm_card_visa", customer=stripe_customer.id
            ),
            country=CountryCode.US,
        )
        au_stripe_payment_method = stripe.clone_payment_method(
            request=ClonePaymentMethodRequest(
                payment_method=PaymentMethodId(stripe_payment_method.id),
                customer=stripe_customer.id,
                stripe_account=STRIPE_PLATFORM_ACCOUNT_IDS[CountryCode.AU],
            ),
            country=CountryCode.US,
        )
        au_stripe_customer = stripe.create_customer(
            request=StripeCreateCustomerRequest(
                email="hahn+aus@doordash.com", description="Hello!"
            ),
            country=CountryCode.AU,
        )
        au_stripe_payment_method = stripe.attach_payment_method(
            request=StripeAttachPaymentMethodRequest(
                payment_method=au_stripe_payment_method.id,
                customer=au_stripe_customer.id,
            ),
            country=CountryCode.AU,
        )
        assert au_stripe_payment_method.customer == au_stripe_customer.id

    @pytest.mark.vcr()
    def test_create_card(self, mode: str, stripe: StripeClient):
        if mode == "mock":
            pytest.skip()

        stripe_customer = stripe.create_customer(
            request=StripeCreateCustomerRequest(
                email="hahn@doordash.com", description="Hello!"
            ),
            country=CountryCode.US,
        )
        stripe_card = stripe.create_card(
            request=StripeCreateCardRequest(
                customer=stripe_customer.id, source=TokenId("tok_visa")
            ),
            country=CountryCode.US,
        )
        assert stripe_card.id.startswith("card_")

    @pytest.mark.vcr()
    def test_clone_card(self, mode: str, stripe: StripeClient):
        if mode == "mock":
            pytest.skip()

        stripe_customer = stripe.create_customer(
            request=StripeCreateCustomerRequest(
                email="hahn@doordash.com", description="Hello!"
            ),
            country=CountryCode.US,
        )
        stripe_card = stripe.create_card(
            request=StripeCreateCardRequest(
                customer=stripe_customer.id, source=TokenId("tok_visa")
            ),
            country=CountryCode.US,
        )
        stripe_payment_method = stripe.clone_payment_method(
            request=ClonePaymentMethodRequest(
                payment_method=PaymentMethodId(stripe_card.id),
                customer=stripe_customer.id,
                stripe_account=STRIPE_PLATFORM_ACCOUNT_IDS[CountryCode.AU],
            ),
            country=CountryCode.US,
        )
        assert stripe_payment_method.id.startswith("pm_")

    def test_create_external_account_card(
        self, mode: str, stripe_test: StripeTestClient
    ):
        if mode == "mock":
            pytest.skip()
        account = prepare_and_validate_stripe_account(stripe_test)
        card = stripe_test.create_external_account_card(
            request=models.CreateExternalAccountRequest(
                country=CountryCode.US,
                type=PayoutExternalAccountType.CARD.value,
                stripe_account_id=account.id,
                external_account_token=VISA_DEBIT_CARD_TOKEN,
            )
        )
        assert card
        assert card.object == "card"
        assert card.id.startswith("card_")

    def test_retrieve_account_token(self, mode: str, stripe: StripeClient):
        if mode == "mock":
            pytest.skip()
        # Creating test account first - to make sure they always exist
        created_account = prepare_and_validate_stripe_account(stripe)
        assert created_account
        assert created_account.id
        account = stripe.retrieve_stripe_account(
            request=RetrieveAccountRequest(
                account_id=created_account.id, country=CountryCode.US
            )
        )

        assert account
        assert account.id == created_account.id


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
        customer = await stripe_async_client.create_customer(
            country=models.CountryCode.US,
            request=models.StripeCreateCustomerRequest(
                email="test@user.com", description="customer name"
            ),
        )
        assert customer
