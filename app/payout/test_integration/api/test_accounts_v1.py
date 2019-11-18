from typing import List
import pytest_mock
from starlette.testclient import TestClient

from app.commons.providers.stripe import stripe_models
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.test_integration.constants import (
    VISA_DEBIT_CARD_TOKEN,
    MASTER_CARD_DEBIT_CARD_TOKEN,
    BANK_ACCOUNT_TOKEN,
)
from app.commons.test_integration.utils import prepare_and_validate_stripe_account_token
from app.commons.types import CountryCode, Currency
from app.payout.api.account.v1 import models as account_models
from app.payout.models import PayoutTargetType, PayoutExternalAccountType
from app.payout.test_integration.api import (
    verify_account_url,
    get_account_by_id_url,
    update_account_statement_descriptor,
    get_payout_method_url,
    list_payout_method_url,
    get_onboarding_requirements_by_stages_url,
    get_initiate_payout_url,
    create_payout_method_url_card,
    create_payout_method_url_bank,
)
from app.payout.core.transfer.create_instant_payout import CreateInstantPayoutResponse


class TestAccountV1:
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
            json={"statement_descriptor": "update_statement_descriptor"},
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
        updated_create_account_token_data = stripe_models.CreateAccountTokenMetaDataRequest(
            business_type="individual",
            individual=stripe_models.Individual(
                first_name=first_name,
                last_name=last_name,
                dob=stripe_models.DateOfBirth(day=5, month=5, year=1991),
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
        new_token = prepare_and_validate_stripe_account_token(
            stripe_client=stripe_test, data=updated_create_account_token_data
        )
        verification_details_request = account_models.VerificationDetailsWithToken(
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

    def test_add_payout_method_card(
        self, client: TestClient, verified_payout_account: dict
    ):
        request = account_models.CreatePayoutMethod(
            token=VISA_DEBIT_CARD_TOKEN, type=PayoutExternalAccountType.CARD
        )
        response = client.post(
            create_payout_method_url_card(verified_payout_account["id"]),
            json=request.dict(),
        )
        assert response.status_code == 201
        payout_card_internal: dict = response.json()
        assert payout_card_internal["stripe_card_id"]
        assert payout_card_internal["type"] == PayoutExternalAccountType.CARD

    def test_add_payout_method_bank(
        self, client: TestClient, verified_payout_account: dict
    ):
        request = account_models.CreatePayoutMethod(
            token=BANK_ACCOUNT_TOKEN, type=PayoutExternalAccountType.BANK_ACCOUNT
        )
        response = client.post(
            create_payout_method_url_bank(verified_payout_account["id"]),
            json=request.dict(),
        )
        assert response.status_code == 201
        payout_card_internal: dict = response.json()
        assert payout_card_internal["bank_name"]
        assert payout_card_internal["type"] == PayoutExternalAccountType.BANK_ACCOUNT

    def test_get_payout_method(self, client: TestClient, verified_payout_account: dict):
        request = account_models.CreatePayoutMethod(
            token=VISA_DEBIT_CARD_TOKEN, type=PayoutExternalAccountType.CARD
        )
        response = client.post(
            create_payout_method_url_card(verified_payout_account["id"]),
            json=request.dict(),
        )
        assert response.status_code == 201
        created_payout_card: dict = response.json()
        assert created_payout_card["stripe_card_id"]

        get_response = client.get(
            get_payout_method_url(
                account_id=verified_payout_account["id"],
                payout_method_id=created_payout_card["id"],
            )
        )
        assert get_response.status_code == 200
        get_payout_card: dict = get_response.json()
        assert get_payout_card == created_payout_card

    def test_list_payout_method(
        self, client: TestClient, verified_payout_account: dict
    ):
        expected_card_list: List[dict] = []
        request_visa = account_models.CreatePayoutMethod(
            token=VISA_DEBIT_CARD_TOKEN, type=PayoutExternalAccountType.CARD
        )
        response_visa = client.post(
            create_payout_method_url_card(verified_payout_account["id"]),
            json=request_visa.dict(),
        )
        assert response_visa.status_code == 201
        created_payout_card_visa: dict = response_visa.json()
        assert created_payout_card_visa["stripe_card_id"]
        # after the next card inserted, the is_default of this card will be unset
        created_payout_card_visa["is_default"] = False
        expected_card_list.insert(0, created_payout_card_visa)

        request_mastercard = account_models.CreatePayoutMethod(
            token=MASTER_CARD_DEBIT_CARD_TOKEN, type=PayoutExternalAccountType.CARD
        )
        response_mastercard = client.post(
            create_payout_method_url_card(verified_payout_account["id"]),
            json=request_mastercard.dict(),
        )
        assert response_mastercard.status_code == 201
        created_payout_card_mastercard: dict = response_mastercard.json()
        assert created_payout_card_mastercard["stripe_card_id"]
        expected_card_list.insert(0, created_payout_card_mastercard)

        # create a bank account
        expected_bank_account_list: List[dict] = []
        request_bank = account_models.CreatePayoutMethod(
            token=BANK_ACCOUNT_TOKEN, type=PayoutExternalAccountType.BANK_ACCOUNT
        )
        response_bank = client.post(
            create_payout_method_url_bank(verified_payout_account["id"]),
            json=request_bank.dict(),
        )
        assert response_bank.status_code == 201
        created_payout_bank_account: dict = response_bank.json()
        assert created_payout_bank_account["bank_last4"]
        expected_bank_account_list.insert(0, created_payout_bank_account)

        # get bank account only
        get_bank_account_response = client.get(
            list_payout_method_url(account_id=verified_payout_account["id"]),
            params={"payout_method_type": "bank_account"},
        )
        assert get_bank_account_response.status_code == 200
        get_payout_method_list_bank_account: dict = get_bank_account_response.json()
        actual_card_list = get_payout_method_list_bank_account["card_list"]
        assert len(actual_card_list) == 0
        actual_bank_account_list = get_payout_method_list_bank_account[
            "bank_account_list"
        ]
        assert len(actual_bank_account_list) == len(expected_bank_account_list)
        assert actual_bank_account_list == expected_bank_account_list

        # get card
        get_response = client.get(
            list_payout_method_url(account_id=verified_payout_account["id"])
        )
        assert get_response.status_code == 200
        get_payout_method_list: dict = get_response.json()
        actual_card_list = get_payout_method_list["card_list"]
        actual_bank_account_list = get_payout_method_list["bank_account_list"]
        assert len(actual_card_list) == len(expected_card_list)
        assert len(actual_bank_account_list) == 0
        assert get_payout_method_list["count"] == len(actual_card_list)
        assert actual_card_list == expected_card_list

        # get with limit
        get_response_with_limit = client.get(
            list_payout_method_url(account_id=verified_payout_account["id"], limit=1)
        )
        assert get_response_with_limit
        get_response_with_limit_response: dict = get_response_with_limit.json()
        assert len(get_response_with_limit_response["card_list"]) == 1
        actual_card = get_response_with_limit_response["card_list"][0]
        assert actual_card["brand"] == "MasterCard"
        assert get_response_with_limit_response["count"] == 1

    def test_get_onboarding_requirements_by_stages(self, client: TestClient):
        response = client.get(
            get_onboarding_requirements_by_stages_url(),
            params={
                "entity_type": PayoutTargetType.STORE,
                "country_shortname": CountryCode.CA,
            },
        )

        required_fields = response.json()
        stages = required_fields.get("required_fields_stages")
        assert stages is not None
        # TODO : Nikita use constants and not hard code the field names
        assert "business_name" in stages.get("stage_0")
        assert "tax_id_CA" in stages.get("stage_1")
        assert response.status_code == 200

    def test_initiate_standard_payout(
        self,
        mocker: pytest_mock.MockFixture,
        client: TestClient,
        verified_payout_account: dict,
    ):
        # mock out processor/biz layer logic, test for API layer handling only
        async def mock_standard_pay(req):
            return CreateInstantPayoutResponse()

        mocker.patch(
            "app.payout.core.account.processor.PayoutAccountProcessors.create_standard_payout",
            side_effect=mock_standard_pay,
        )

        request_body = account_models.InitiatePayoutRequest(
            amount=100,
            payout_type="standard",
            statement_descriptor="test_initiate_payout-api-call",
            target_id=1,
            target_type="store",
            transfer_id=100,
            method="stripe",
        )
        response = client.post(
            get_initiate_payout_url(verified_payout_account["id"]),
            json=request_body.dict(),
        )
        assert response.status_code == 200
        assert response.json() == {"id": 0}

    def test_initiate_fast_payout(
        self,
        mocker: pytest_mock.MockFixture,
        client: TestClient,
        verified_payout_account_with_payout_card: dict,
    ):
        # mock out processor/biz layer logic, test for API layer handling only
        async def mock_fast_pay(req):
            return CreateInstantPayoutResponse()

        mocker.patch(
            "app.payout.core.account.processor.PayoutAccountProcessors.create_instant_payout",
            side_effect=mock_fast_pay,
        )

        request_body = account_models.InitiatePayoutRequest(
            amount=100,
            payout_type="instant",
            statement_descriptor="test_initiate_payout-api-call",
            target_id=1,
            target_type="store",
            payout_id=100,
            method="stripe",
            payout_idempotency_key="test_initiate_payout-api-call-ik",
        )
        response = client.post(
            get_initiate_payout_url(verified_payout_account_with_payout_card["id"]),
            json=request_body.dict(),
        )
        assert response.status_code == 200
        assert response.json() == {"id": 0}
