import json
import random

from starlette.testclient import TestClient
from app.commons.api.errors import BadRequestErrorCode, payment_error_message_maps
from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.test_integration.constants import VISA_DEBIT_CARD_TOKEN
from app.commons.types import CountryCode, Currency
from app.payout.api.instant_payout.v1 import models as instant_payout_models
from app.payout.api.transaction.v1 import models as transaction_models
from app.payout.core.errors import InstantPayoutErrorCode
from app.payout.core.instant_payout.models import (
    PaymentEligibilityReasons,
    InstantPayoutFees,
    InstantPayoutCardChangeBlockTimeInDays,
    InternalPaymentEligibility,
    payment_eligibility_reason_details,
)
from app.commons.providers.stripe import stripe_models
import pytest
import app.payout.api.account.v1.models as account_models
from app.payout.core.instant_payout.utils import create_idempotency_key
from app.payout.models import (
    PayoutAccountTargetType,
    StripeAccountToken,
    PayoutExternalAccountType,
)
from app.payout.test_integration.api import (
    create_account_url,
    verify_account_url,
    create_payout_method_url_card,
)

INSTANT_PAYOUT_ENDPOINT = "/payout/api/v1/instant_payouts/"
TRANSACTION_ENDPOINT = "/payout/api/v1/transactions/"


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
            create_payout_method_url_card(verified_payout_account["id"]),
            json=request.dict(),
        )
        assert response.status_code == 201
        return verified_payout_account

    def test_not_eligible_due_to_payout_account_not_exist(self, client: TestClient):
        payout_account_id = random.randint(1, 2147483647)
        url = INSTANT_PAYOUT_ENDPOINT + str(payout_account_id) + "/eligibility"
        response = client.get(url, params={"local_start_of_day": 11111})
        assert response.status_code == 200
        expected = InternalPaymentEligibility(
            payout_account_id=payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST
            ],
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
            response.json().get("error_code") == BadRequestErrorCode.INVALID_VALUE_ERROR
        )
        assert (
            response.json().get("error_message")
            == payment_error_message_maps[BadRequestErrorCode.INVALID_VALUE_ERROR]
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
            payout_account_id=payout_account_dx.get("id"),
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP
            ],
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
            payout_account_id=payout_account_mx.get("id"),
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_TYPE_NOT_SUPPORTED,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.PAYOUT_ACCOUNT_TYPE_NOT_SUPPORTED
            ],
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
            payout_account_id=verified_payout_account.get("id"),
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_CARD_NOT_SETUP,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.PAYOUT_CARD_NOT_SETUP
            ],
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
        eligibility = response.json()
        assert eligibility.get(
            "payout_account_id"
        ) == verified_payout_account_with_payout_card.get("id")
        assert eligibility.get("eligible") is False
        assert (
            eligibility.get("reason")
            == PaymentEligibilityReasons.PAYOUT_CARD_CHANGED_RECENTLY
        )
        assert eligibility.get("fee") == InstantPayoutFees.STANDARD_FEE
        details = json.loads(eligibility.get("details"))
        assert details.get("num_days_blocked") == InstantPayoutCardChangeBlockTimeInDays
        assert len(details.get("cards_changed")) > 0
        assert type(details.get("cards_changed")) == list
        assert type(details.get("cards_changed")[0]) == dict


class TestSubmitInstantPayout:
    @pytest.fixture(autouse=True)
    def setup(self, verified_payout_account_with_payout_card: dict):
        self.payout_account_id = verified_payout_account_with_payout_card["id"]
        self.stripe_card_id = verified_payout_account_with_payout_card["stripe_card_id"]

    def test_successful_submit_instant_payout_when_specify_card(
        self, verified_payout_account_with_payout_card: dict, client: TestClient
    ):
        # Create one transactions
        transaction_amount = 1100
        test_idempotency_key = create_idempotency_key(prefix="test-create-transaction")
        tx_creation_req = transaction_models.TransactionCreate(
            amount=transaction_amount,
            payment_account_id=self.payout_account_id,
            idempotency_key=test_idempotency_key,
            target_id=1,
            target_type="dasher_job",
            currency="usd",
        )
        response = client.post(TRANSACTION_ENDPOINT, json=tx_creation_req.dict())
        assert response.status_code == 201
        instant_payout_create = instant_payout_models.InstantPayoutCreate(
            payout_account_id=self.payout_account_id,
            amount=transaction_amount,
            currency="usd",
            card=self.stripe_card_id,
        )
        response = client.post(
            INSTANT_PAYOUT_ENDPOINT, json=instant_payout_create.dict()
        )
        assert response.status_code == 200
        response_data = response.json()

        assert response_data.get("payout_account_id") == self.payout_account_id
        assert isinstance(response_data.get("payout_id"), int)
        assert (
            response_data.get("amount")
            == transaction_amount - InstantPayoutFees.STANDARD_FEE
        )
        assert response_data.get("currency") == "usd"
        assert response_data.get("fee") == InstantPayoutFees.STANDARD_FEE
        assert response_data.get("card") == self.stripe_card_id
        assert response_data.get("created_at") is not None

    def test_successful_submit_instant_payout_when_not_specify_card(
        self, verified_payout_account_with_payout_card: dict, client: TestClient
    ):
        # Create one transactions
        transaction_amount = 3000
        test_idempotency_key = create_idempotency_key(prefix="test-create-transaction")
        tx_creation_req = transaction_models.TransactionCreate(
            amount=transaction_amount,
            payment_account_id=self.payout_account_id,
            idempotency_key=test_idempotency_key,
            target_id=1,
            target_type="dasher_job",
            currency="usd",
        )
        response = client.post(TRANSACTION_ENDPOINT, json=tx_creation_req.dict())
        assert response.status_code == 201
        instant_payout_create = instant_payout_models.InstantPayoutCreate(
            payout_account_id=self.payout_account_id,
            amount=transaction_amount,
            currency="usd",
        )
        response = client.post(
            INSTANT_PAYOUT_ENDPOINT, json=instant_payout_create.dict()
        )
        assert response.status_code == 200
        response_data = response.json()

        assert response_data.get("payout_account_id") == self.payout_account_id
        assert isinstance(response_data.get("payout_id"), int)
        assert (
            response_data.get("amount")
            == transaction_amount - InstantPayoutFees.STANDARD_FEE
        )
        assert response_data.get("currency") == "usd"
        assert response_data.get("fee") == InstantPayoutFees.STANDARD_FEE
        assert response_data.get("card") == self.stripe_card_id
        assert response_data.get("created_at") is not None

    def test_get_bad_request_error_when_no_payout_account_found(
        self, client: TestClient
    ):
        payout_account_id = random.randint(1, 2147483647)
        instant_payout_create = instant_payout_models.InstantPayoutCreate(
            payout_account_id=payout_account_id, amount=200, currency="usd"
        )
        response = client.post(
            INSTANT_PAYOUT_ENDPOINT, json=instant_payout_create.dict()
        )
        # Should raise 400 BadRequestError with error message of Payout Account not exist
        assert response.status_code == 400
        assert response.json()["error_code"] == InstantPayoutErrorCode.INVALID_REQUEST
        assert (
            response.json()["error_message"]
            == PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST
        )


class TestGetInstantPayoutByPayoutAccountId:
    def test_get_instant_payouts(
        self, prepared_payouts_and_stripe_payout_requests_data: dict, client: TestClient
    ):
        payout_account_id = prepared_payouts_and_stripe_payout_requests_data.get(
            "payout_account_id"
        )
        prepared_records = prepared_payouts_and_stripe_payout_requests_data.get(
            "items", []
        )

        # Get latest 2 payouts
        url = INSTANT_PAYOUT_ENDPOINT + str(payout_account_id) + "/payouts"
        response = client.get(url, params={"limit": 2})
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["count"] == 2
        assert response_json["cursor"] is not None
        # retrieved payouts should be the latest 2
        assert response_json.get("instant_payouts", []) == [
            prepared_records[-1],
            prepared_records[-2],
        ]

        # Use the new cursor to retrieve another 2
        new_cursor = response_json["cursor"]
        response = client.get(url, params={"limit": 2, "cursor": new_cursor})
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["count"] == 2
        assert response_json["cursor"] is not None
        # retrieved payouts should be the next 2
        assert response_json["instant_payouts"] == [
            prepared_records[-3],
            prepared_records[-4],
        ]

        # Use the new cursor to retrieve last one
        new_cursor = response_json["cursor"]
        response = client.get(url, params={"limit": 3, "cursor": new_cursor})
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["count"] == 1
        assert response_json["cursor"] is None  # cursor should be None now
        # retrieved payouts should be the next 2
        assert response_json["instant_payouts"] == [prepared_records[-5]]
