import pytest
from starlette.testclient import TestClient

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.types import CountryCode
from app.payout.types import StripeAccountToken

ACCOUNT_ENDPOINT = "/payout/api/v1/accounts"


def create_account_url():
    return ACCOUNT_ENDPOINT + "/"


def get_account_by_id_url(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}"


def update_account_statement_descriptor(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}/statement_descriptor"


def verify_account_url(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}/verify/legacy"


class TestAccountV1:
    @pytest.fixture
    def stripe_test(self, stripe_api, app_config: AppConfig):
        # allow this test to directly call stripe to create account token
        stripe_api.enable_outbound()

        return StripeTestClient(
            [
                models.StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ]
        )

    @pytest.fixture
    def account_token(self, stripe_test: StripeTestClient) -> StripeAccountToken:
        data = models.CreateAccountTokenMetaData(
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
        account_token = stripe_test.create_account_token(
            request=models.CreateAccountTokenRequest(
                account=data, country=CountryCode.US
            )
        )
        return account_token.id

    def test_invalid(self, client: TestClient):
        response = client.get(ACCOUNT_ENDPOINT + "/")
        assert response.status_code == 405, "accessing accounts requires an id"

    def test_create_get_verify_payout_account(
        self, client: TestClient, account_token: StripeAccountToken
    ):
        account_to_create = {
            "target_id": 1,
            "target_type": "dasher",
            "country": "US",
            "currency": "usd",
            "statement_descriptor": "test_statement_descriptor",
        }

        #  Create
        response = client.post(create_account_url(), json=account_to_create)
        assert response.status_code == 201
        account_created: dict = response.json()
        assert (
            account_created["statement_descriptor"]
            == account_to_create["statement_descriptor"]
        )

        #  Get
        response = client.get(get_account_by_id_url(account_created["id"]))

        assert response.status_code == 200
        account_got_by_id: dict = response.json()
        assert account_got_by_id == account_created

        # Update statement_descriptor
        response = client.patch(
            update_account_statement_descriptor(account_created["id"]),
            params={"statement_descriptor": "update_statement_descriptor"},
        )
        assert response.status_code == 200

        # Verify
        verification_details = {
            "account_token": account_token,
            "currency": "usd",
            "country": "US",
        }
        response = client.post(
            verify_account_url(account_created["id"]), json=verification_details
        )
        assert response.status_code == 200
