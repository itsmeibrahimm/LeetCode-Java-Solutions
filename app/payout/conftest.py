import pytest

from starlette.testclient import TestClient

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe import stripe_models
from app.commons.providers.stripe.stripe_client import (
    StripeTestClient,
    StripeClient,
    StripeAsyncClient,
)
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import StripeClientSettings
from app.commons.test_integration.constants import VISA_DEBIT_CARD_TOKEN
from app.commons.types import CountryCode, Currency
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.api.account.v1 import models as account_models
from app.payout.models import (
    StripeAccountToken,
    PayoutAccountTargetType,
    PayoutExternalAccountType,
)
from app.payout.test_integration.api import (
    create_account_url,
    verify_account_url,
    create_payout_method_url,
)


@pytest.fixture
def stripe_async_client(stripe_api, app_config: AppConfig):
    stripe_api.enable_outbound()

    stripe_client = StripeClient(
        settings_list=[
            StripeClientSettings(
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


@pytest.fixture
def stripe_test(stripe_api, app_config: AppConfig):
    # allow this test to directly call stripe to create account token
    stripe_api.enable_outbound()

    return StripeTestClient(
        [
            stripe_models.StripeClientSettings(
                api_key=app_config.STRIPE_US_SECRET_KEY.value, country=CountryCode.US
            ),
            stripe_models.StripeClientSettings(
                api_key=app_config.STRIPE_CA_SECRET_KEY.value, country=CountryCode.CA
            ),
            stripe_models.StripeClientSettings(
                api_key=app_config.STRIPE_AU_SECRET_KEY.value, country=CountryCode.AU
            ),
        ]
    )


@pytest.fixture
def account_token(stripe_test: StripeTestClient) -> StripeAccountToken:
    data = stripe_models.CreateAccountTokenMetaDataRequest(
        business_type="individual",
        individual=stripe_models.Individual(
            first_name="Test",
            last_name="Payment",
            dob=stripe_models.DateOfBirth(day=1, month=1, year=1990),
            address=stripe_models.Address(
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
    account_token = stripe_test.create_account_token(
        request=stripe_models.CreateAccountTokenRequest(
            account=data, country=CountryCode.US
        )
    )
    return account_token.id


@pytest.fixture
def create_payout_account() -> account_models.CreatePayoutAccount:
    return account_models.CreatePayoutAccount(
        target_id=1,
        target_type=PayoutAccountTargetType.DASHER,
        country=CountryCode.US,
        currency=Currency.USD,
        statement_descriptor="test_statement_descriptor",
    )


@pytest.fixture
def payout_account(
    client: TestClient, create_payout_account: account_models.CreatePayoutAccount
) -> dict:
    response = client.post(create_account_url(), json=create_payout_account.dict())
    assert response.status_code == 201
    account_created: dict = response.json()
    assert (
        account_created["statement_descriptor"]
        == create_payout_account.statement_descriptor
    ), "created payout account's statement_descriptor matches with expected"
    return account_created


@pytest.fixture
def verified_payout_account(
    client: TestClient, account_token: StripeAccountToken, payout_account: dict
) -> dict:
    # Verify to create pgp account
    verification_details_request = account_models.VerificationDetailsWithToken(
        account_token=account_token, country=CountryCode.US, currency=Currency.USD
    )
    response = client.post(
        verify_account_url(payout_account["id"]),
        json=verification_details_request.dict(),
    )
    verified_account: dict = response.json()
    assert response.status_code == 200
    assert verified_account["pgp_account_id"]
    assert verified_account["pgp_external_account_id"]
    return verified_account


@pytest.fixture
def verified_payout_account_with_payout_card(
    client: TestClient, verified_payout_account: dict
) -> dict:
    request = account_models.CreatePayoutMethod(
        token=VISA_DEBIT_CARD_TOKEN, type=PayoutExternalAccountType.CARD
    )
    response = client.post(
        create_payout_method_url(verified_payout_account["id"]), json=request.dict()
    )
    assert response.status_code == 201
    verified_payout_account["stripe_card_id"] = response.json()["stripe_card_id"]
    return verified_payout_account
