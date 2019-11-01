import random

from asynctest import ANY
from starlette.testclient import TestClient
from app.commons.api.errors import InvalidRequestErrorCode, payment_error_message_maps
from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.test_integration.constants import VISA_DEBIT_CARD_TOKEN
from app.commons.types import CountryCode, Currency
from app.payout.core.instant_payout.models import (
    PaymentEligibilityReasons,
    InstantPayoutFees,
    InstantPayoutCardChangeBlockTimeInDays,
    InternalPaymentEligibility,
)
from app.commons.providers.stripe import stripe_models
import pytest
import app.payout.api.account.v1.models as account_models
from app.payout.models import (
    PayoutAccountTargetType,
    StripeAccountToken,
    PayoutExternalAccountType,
)
from app.payout.test_integration.api import (
    create_account_url,
    verify_account_url,
    create_payout_method_url,
)

INSTANT_PAYOUT_ENDPOINT = "/payout/api/v1/instant_payouts/"


class TestCheckInstantPayoutEligibility:
    @pytest.fixture
    def stripe_test(self, stripe_api, app_config: AppConfig):
        # allow this test to directly call stripe to create account token
        stripe_api.enable_outbound()

        return StripeTestClient(
            [
                stripe_models.StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value,
                    country=CountryCode.US,
                ),
                stripe_models.StripeClientSettings(
                    api_key=app_config.STRIPE_CA_SECRET_KEY.value,
                    country=CountryCode.CA,
                ),
                stripe_models.StripeClientSettings(
                    api_key=app_config.STRIPE_AU_SECRET_KEY.value,
                    country=CountryCode.AU,
                ),
            ]
        )

    @pytest.fixture
    def payout_account_dx(self, client: TestClient) -> dict:
        create_payment_account_req = account_models.CreatePayoutAccount(
            target_id=1,
            target_type=PayoutAccountTargetType.DASHER,
            country=CountryCode.US,
            currency=Currency.USD,
            statement_descriptor="test_statement_descriptor",
        )
        response = client.post(
            create_account_url(), json=create_payment_account_req.dict()
        )
        assert response.status_code == 201
        account_created: dict = response.json()
        assert (
            account_created["statement_descriptor"]
            == create_payment_account_req.statement_descriptor
        ), "created payout account's statement_descriptor matches with expected"
        return account_created

    @pytest.fixture
    def payout_account_mx(self, client: TestClient) -> dict:
        create_payment_account_req = account_models.CreatePayoutAccount(
            target_id=1,
            target_type=PayoutAccountTargetType.STORE,
            country=CountryCode.US,
            currency=Currency.USD,
            statement_descriptor="test_statement_descriptor",
        )
        response = client.post(
            create_account_url(), json=create_payment_account_req.dict()
        )
        assert response.status_code == 201
        account_created: dict = response.json()
        assert (
            account_created["statement_descriptor"]
            == create_payment_account_req.statement_descriptor
        ), "created payout account's statement_descriptor matches with expected"
        return account_created

    @pytest.fixture
    def account_token(self, stripe_test: StripeTestClient) -> StripeAccountToken:
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
    def verified_payout_account(
        self,
        client: TestClient,
        account_token: StripeAccountToken,
        payout_account_dx: dict,
    ) -> dict:
        # Verify to create pgp account
        verification_details_request = account_models.VerificationDetailsWithToken(
            account_token=account_token, country=CountryCode.US, currency=Currency.USD
        )
        response = client.post(
            verify_account_url(payout_account_dx["id"]),
            json=verification_details_request.dict(),
        )
        verified_account: dict = response.json()
        assert response.status_code == 200
        assert verified_account["pgp_account_id"]
        assert verified_account["pgp_external_account_id"]
        return verified_account

    @pytest.fixture
    def verified_payout_account_with_payout_card(
        self, client: TestClient, verified_payout_account: dict
    ) -> dict:
        request = account_models.CreatePayoutMethod(
            token=VISA_DEBIT_CARD_TOKEN, type=PayoutExternalAccountType.CARD
        )
        response = client.post(
            create_payout_method_url(verified_payout_account["id"]), json=request.dict()
        )
        assert response.status_code == 201
        return verified_payout_account

    def test_not_eligible_due_to_payout_account_not_exist(self, client: TestClient):
        payout_account_id = random.randint(1, 2147483647)
        url = INSTANT_PAYOUT_ENDPOINT + str(payout_account_id) + "/eligibility"
        response = client.get(url, params={"local_start_of_day": 11111})
        assert response.status_code == 200
        expected = InternalPaymentEligibility(
            eligible=False, reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST
        ).dict()
        assert response.json() == expected

    def test_local_start_of_day_cause_overflow(self, client: TestClient):
        payout_account_id = 123
        local_start_of_day = 99999999999999999999
        url = INSTANT_PAYOUT_ENDPOINT + str(payout_account_id) + "/eligibility"
        response = client.get(url, params={"local_start_of_day": local_start_of_day})
        # Should return 400 bad request error
        assert response.status_code == 400
        assert (
            response.json().get("error_code")
            == InvalidRequestErrorCode.INVALID_VALUE_ERROR
        )
        assert (
            response.json().get("error_message")
            == payment_error_message_maps[InvalidRequestErrorCode.INVALID_VALUE_ERROR]
        )

    def test_not_eligible_due_to_pgp_account_not_setup(
        self, client: TestClient, payout_account_dx: dict
    ):
        url = (
            INSTANT_PAYOUT_ENDPOINT + str(payout_account_dx.get("id")) + "/eligibility"
        )
        response = client.get(url, params={"local_start_of_day": 11111})
        assert response.status_code == 200
        expected = InternalPaymentEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP,
            fee=InstantPayoutFees.STANDARD_FEE,
        ).dict()
        assert response.json() == expected

    def test_not_eligible_due_to_payout_account_entity_not_supported(
        self, client: TestClient, payout_account_mx: dict
    ):
        url = (
            INSTANT_PAYOUT_ENDPOINT + str(payout_account_mx.get("id")) + "/eligibility"
        )
        response = client.get(url, params={"local_start_of_day": 11111})
        assert response.status_code == 200
        expected = InternalPaymentEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_TYPE_NOT_SUPPORTED,
            fee=InstantPayoutFees.STANDARD_FEE,
        ).dict()
        assert response.json() == expected

    def test_not_eligible_due_to_payout_card_not_setup(
        self, client: TestClient, verified_payout_account: dict
    ):
        url = (
            INSTANT_PAYOUT_ENDPOINT
            + str(verified_payout_account.get("id"))
            + "/eligibility"
        )
        response = client.get(url, params={"local_start_of_day": 11111})
        assert response.status_code == 200
        expected = InternalPaymentEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_CARD_NOT_SETUP,
            fee=InstantPayoutFees.STANDARD_FEE,
        ).dict()
        assert response.json() == expected

    def test_not_eligible_due_to_recently_changed_card(
        self, client: TestClient, verified_payout_account_with_payout_card: dict
    ):
        url = (
            INSTANT_PAYOUT_ENDPOINT
            + str(verified_payout_account_with_payout_card.get("id"))
            + "/eligibility"
        )
        response = client.get(url, params={"local_start_of_day": 11111})
        assert response.status_code == 200
        expected = InternalPaymentEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_CARD_CHANGED_RECENTLY,
            details={
                "num_days_blocked": InstantPayoutCardChangeBlockTimeInDays,
                "cards_changed": [ANY],
            },
            fee=InstantPayoutFees.STANDARD_FEE,
        ).dict()
        assert response.json() == expected
