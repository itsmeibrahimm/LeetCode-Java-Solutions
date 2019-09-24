import pytest
from starlette.testclient import TestClient

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.test_integration.constants import DEBIT_CARD_TOKEN
from app.commons.types import CountryCode, Currency
from app.payout.api.account.v1.models import (
    CreatePayoutAccount,
    VerificationDetailsWithToken,
    CreatePayoutMethod,
)
from app.payout.types import (
    StripeAccountToken,
    PayoutTargetType,
    PayoutAccountTargetType,
    PayoutExternalAccountType,
)

ACCOUNT_ENDPOINT = "/payout/api/v1/accounts"


def create_account_url():
    return ACCOUNT_ENDPOINT + "/"


def get_account_by_id_url(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}"


def update_account_statement_descriptor(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}/statement_descriptor"


def verify_account_url(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}/verify/legacy"


def create_payout_method_url(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}/payout_methods"


def get_onboarding_requirements_by_stages_url(
    entity_type: PayoutTargetType, country_shortname: CountryCode
):
    return f"{ACCOUNT_ENDPOINT}/onboarding_required_fields/{entity_type}/{country_shortname}"


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
        data = models.CreateAccountTokenMetaDataRequest(
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

    @pytest.fixture
    def create_payout_account(self) -> CreatePayoutAccount:
        return CreatePayoutAccount(
            target_id=1,
            target_type=PayoutAccountTargetType.DASHER,
            country=CountryCode.US,
            currency=Currency.USD,
            statement_descriptor="test_statement_descriptor",
        )

    def test_invalid(self, client: TestClient):
        response = client.get(ACCOUNT_ENDPOINT + "/")
        assert response.status_code == 405, "accessing accounts requires an id"

    def test_create_payout_account(
        self, client: TestClient, create_payout_account: CreatePayoutAccount
    ):
        response = client.post(create_account_url(), json=create_payout_account.dict())
        assert response.status_code == 201
        account_created: dict = response.json()
        assert (
            account_created["statement_descriptor"]
            == create_payout_account.statement_descriptor
        ), "created payout account's statement_descriptor matches with expected"
        return account_created

    def test_get_payout_account(
        self, client: TestClient, create_payout_account: CreatePayoutAccount
    ):
        account_created = self.test_create_payout_account(client, create_payout_account)
        response = client.get(get_account_by_id_url(account_created["id"]))
        assert response.status_code == 200
        retrieved_account: dict = response.json()
        assert retrieved_account == account_created

    def test_update_account_statement_descriptor(
        self, client: TestClient, create_payout_account: CreatePayoutAccount
    ):
        account_created = self.test_create_payout_account(client, create_payout_account)
        response = client.patch(
            update_account_statement_descriptor(account_created["id"]),
            params={"statement_descriptor": "update_statement_descriptor"},
        )
        updated_account: dict = response.json()
        assert response.status_code == 200
        assert updated_account["statement_descriptor"] == "update_statement_descriptor"

    def test_verify_payout_account(
        self,
        client: TestClient,
        account_token: StripeAccountToken,
        create_payout_account: CreatePayoutAccount,
    ):
        account_created = self.test_create_payout_account(client, create_payout_account)

        # Verify
        verification_details_request = VerificationDetailsWithToken(
            account_token=account_token, country=CountryCode.US, currency=Currency.USD
        )
        response = client.post(
            verify_account_url(account_created["id"]),
            json=verification_details_request.dict(),
        )
        verified_account: dict = response.json()
        assert response.status_code == 200
        assert verified_account["pgp_account_id"]
        assert verified_account["pgp_external_account_id"]
        return verified_account

    def test_add_payout_method(
        self,
        client: TestClient,
        account_token: StripeAccountToken,
        create_payout_account: CreatePayoutAccount,
    ):
        # set up account
        account = self.test_verify_payout_account(
            client, account_token, create_payout_account
        )
        request = CreatePayoutMethod(
            token=DEBIT_CARD_TOKEN, type=PayoutExternalAccountType.CARD
        )
        response = client.post(
            create_payout_method_url(account["id"]), json=request.dict()
        )
        assert response.status_code == 201
        payout_card_internal: dict = response.json()
        assert payout_card_internal["stripe_card_id"]

    def test_get_onboarding_requirements_by_stages(self, client: TestClient):
        response = client.get(
            get_onboarding_requirements_by_stages_url(
                PayoutTargetType.STORE, CountryCode.CA
            )
        )

        required_fields = response.json()
        stages = required_fields.get("required_fields_stages")
        assert stages is not None
        # TODO : Nikita use constants and not hard code the field names
        assert "business_name" in stages.get("stage_0")
        assert "tax_id_CA" in stages.get("stage_1")
        assert response.status_code == 200
