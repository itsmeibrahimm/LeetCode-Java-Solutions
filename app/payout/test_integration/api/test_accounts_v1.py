import pytest
from starlette.testclient import TestClient

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.providers.stripe.stripe_models import CreateAccountTokenMetaDataRequest
from app.commons.test_integration.constants import DEBIT_CARD_TOKEN
from app.commons.test_integration.utils import prepare_and_validate_stripe_account_token
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


def get_account_by_id_url(account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}"


def update_account_statement_descriptor(account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/statement_descriptor"


def verify_account_url(account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/verify/legacy"


def create_payout_method_url(account_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/payout_methods"


def get_payout_method_url(account_id: int, payout_method_id: int):
    return f"{ACCOUNT_ENDPOINT}/{account_id}/payout_methods/{payout_method_id}"


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

    @pytest.fixture
    def payout_account(
        self, client: TestClient, create_payout_account: CreatePayoutAccount
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
        self,
        client: TestClient,
        account_token: StripeAccountToken,
        payout_account: dict,
    ) -> dict:
        # Verify to create pgp account
        verification_details_request = VerificationDetailsWithToken(
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

    def test_invalid(self, client: TestClient):
        response = client.get(ACCOUNT_ENDPOINT + "/")
        assert response.status_code == 405, "accessing accounts requires an id"

    def test_get_payout_account(self, client: TestClient, payout_account: dict):
        response = client.get(get_account_by_id_url(payout_account["id"]))
        assert response.status_code == 200
        retrieved_account: dict = response.json()
        assert retrieved_account == payout_account

    def test_update_account_statement_descriptor(
        self, client: TestClient, payout_account: dict
    ):
        response = client.patch(
            update_account_statement_descriptor(payout_account["id"]),
            params={"statement_descriptor": "update_statement_descriptor"},
        )
        updated_account: dict = response.json()
        assert response.status_code == 200
        assert updated_account["statement_descriptor"] == "update_statement_descriptor"

    def test_verify_payout_account_update(
        self,
        client: TestClient,
        verified_payout_account: dict,
        stripe_test: StripeTestClient,
    ):
        # Verify to update pgp account
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
            stripe_client=stripe_test, data=updated_create_account_token_data
        )
        verification_details_request = VerificationDetailsWithToken(
            account_token=new_token.id, country=CountryCode.US, currency=Currency.USD
        )
        response = client.post(
            verify_account_url(verified_payout_account["id"]),
            json=verification_details_request.dict(),
        )
        verified_account: dict = response.json()
        assert response.status_code == 200
        assert (
            verified_account["pgp_account_id"]
            == verified_payout_account["pgp_account_id"]
        )
        assert (
            verified_account["pgp_external_account_id"]
            == verified_payout_account["pgp_external_account_id"]
        )

    def test_add_payout_method(self, client: TestClient, verified_payout_account: dict):
        request = CreatePayoutMethod(
            token=DEBIT_CARD_TOKEN, type=PayoutExternalAccountType.CARD
        )
        response = client.post(
            create_payout_method_url(verified_payout_account["id"]), json=request.dict()
        )
        assert response.status_code == 201
        payout_card_internal: dict = response.json()
        assert payout_card_internal["stripe_card_id"]

    def test_get_payout_method(self, client: TestClient, verified_payout_account: dict):
        request = CreatePayoutMethod(
            token=DEBIT_CARD_TOKEN, type=PayoutExternalAccountType.CARD
        )
        response = client.post(
            create_payout_method_url(verified_payout_account["id"]), json=request.dict()
        )
        assert response.status_code == 201
        created_payout_card: dict = response.json()
        assert created_payout_card["stripe_card_id"]

        get_response = client.get(
            get_payout_method_url(
                account_id=verified_payout_account["id"],
                payout_method_id=created_payout_card["id"],
            ),
            json=request.dict(),
        )
        assert get_response.status_code == 200
        get_payout_card: dict = get_response.json()
        assert get_payout_card == created_payout_card

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
