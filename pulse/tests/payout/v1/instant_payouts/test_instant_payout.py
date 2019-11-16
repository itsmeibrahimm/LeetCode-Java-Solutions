import json

import pytest
from payout_v1_client import (
    InstantPayoutsV1Api,
    PaymentEligibility,
    ApiException,
    CreatePayoutAccount,
    InstantPayoutCreate,
    AccountsV1Api,
    VerificationDetailsWithToken,
)
import stripe
from tests.payout.v1.accounts.test_payout_account_and_method_crud import (
    STRIPE_US_PUBLIC_API_KEY,
)
from tests.payout.v1.client_operations import (
    check_instant_payout_eligibility,
    submit_instant_payout,
    create_payout_account,
    verify_payout_account_legacy,
)


class TestCheckInstantPayout:
    @pytest.fixture
    def created_dx_us_payout_account(self, accounts_api: AccountsV1Api):
        dx_us_account_create_request = CreatePayoutAccount(
            target_id=12345,
            target_type="dasher",
            country="US",
            currency="usd",
            statement_descriptor="pulse-test-statement-descriptor",
        )
        created_dx_us_payout_account, status, _ = create_payout_account(
            request=dx_us_account_create_request, accounts_api=accounts_api
        )
        yield created_dx_us_payout_account

    @pytest.fixture
    def created_dx_ca_payout_account(self, accounts_api: AccountsV1Api):
        dx_ca_account_create_request = CreatePayoutAccount(
            target_id=12345,
            target_type="dasher",
            country="CA",
            currency="cad",
            statement_descriptor="pulse-test-statement-descriptor",
        )
        created_dx_ca_payout_account, status, _ = create_payout_account(
            request=dx_ca_account_create_request, accounts_api=accounts_api
        )
        yield created_dx_ca_payout_account

    @pytest.fixture
    def created_mx_us_payout_account(self, accounts_api: AccountsV1Api):
        mx_us_account_create_request = CreatePayoutAccount(
            target_id=12345,
            target_type="store",
            country="US",
            currency="usd",
            statement_descriptor="pulse-test-statement-descriptor",
        )
        created_mx_us_payout_account, status, _ = create_payout_account(
            request=mx_us_account_create_request, accounts_api=accounts_api
        )
        yield created_mx_us_payout_account

    @pytest.fixture
    def created_mx_ca_payout_account(self, accounts_api: AccountsV1Api):
        mx_ca_account_create_request = CreatePayoutAccount(
            target_id=12345,
            target_type="store",
            country="CA",
            currency="cad",
            statement_descriptor="pulse-test-statement-descriptor",
        )
        created_mx_ca_payout_account, status, _ = create_payout_account(
            request=mx_ca_account_create_request, accounts_api=accounts_api
        )
        yield created_mx_ca_payout_account

    @pytest.fixture
    def verified_dx_us_payout_account(self, accounts_api: AccountsV1Api):
        dx_us_account_create_request = CreatePayoutAccount(
            target_id=12345,
            target_type="dasher",
            country="US",
            currency="usd",
            statement_descriptor="pulse-test-statement-descriptor",
        )
        created_dx_us_payout_account, status, _ = create_payout_account(
            request=dx_us_account_create_request, accounts_api=accounts_api
        )
        stripe.api_key = STRIPE_US_PUBLIC_API_KEY
        account_token = stripe.Token.create(
            account={
                "business_type": "individual",
                "individual": {"first_name": "Jane", "last_name": "Doe"},
                "tos_shown_and_accepted": True,
            }
        )
        verification_details_with_token = VerificationDetailsWithToken(
            account_token=account_token.get("id"), country="US", currency="usd"
        )

        verified_payout_account, status, _ = verify_payout_account_legacy(
            payout_account_id=created_dx_us_payout_account.id,
            verification_details_with_token=verification_details_with_token,
            accounts_api=accounts_api,
        )
        yield verified_payout_account

    def test_not_eligible_due_to_payout_account_not_exist(
        self, instant_payouts_api: InstantPayoutsV1Api
    ):
        local_start_of_day = 1111
        payout_account_id = -1  # use -1 here to make sure it will not exist in db
        payment_eligibility, status, _ = check_instant_payout_eligibility(
            payout_account_id=payout_account_id,
            local_start_of_day=local_start_of_day,
            instant_payout_api=instant_payouts_api,
        )
        expected = PaymentEligibility(
            payout_account_id=payout_account_id,
            eligible=False,
            reason="payout_account_not_exist",
            details="The payout account id passed in does not exist.",
            balance=None,
            currency=None,
            fee=None,
        )
        assert status == 200
        assert payment_eligibility == expected

        # When submit instant payout now will get 400 bad request error
        instant_payout_create = InstantPayoutCreate(
            payout_account_id=payout_account_id, amount=1111, currency="usd"
        )
        with pytest.raises(ApiException) as e:
            submit_instant_payout(
                instant_payout_create=instant_payout_create,
                instant_payout_api=instant_payouts_api,
            )
        assert e.value.status == 400
        body = json.loads(e.value.body)
        assert body.get("error_code") == "invalid_request"
        assert body.get("error_message") == "payout_account_not_exist"

    def test_raise_exception_when_pass_in_big_local_start_of_day(
        self, instant_payouts_api: InstantPayoutsV1Api
    ):
        # Check pass in a very big local_start_of_day will raise ApiException
        with pytest.raises(ApiException) as e:
            check_instant_payout_eligibility(
                payout_account_id=123,
                local_start_of_day=99999999999999999999,
                instant_payout_api=instant_payouts_api,
            )
        assert e.value.status == 400
        body = json.loads(e.value.body)
        assert body.get("error_code") == "invalid_value_error"
        assert body.get("error_message") == "Field value is invalid."

    def test_not_eligible_due_to_pgp_account_not_setup(
        self, created_dx_us_payout_account, instant_payouts_api: InstantPayoutsV1Api
    ):
        # Check eligibility, not eligible due to no pgp account
        payment_eligibility, status, _ = check_instant_payout_eligibility(
            payout_account_id=created_dx_us_payout_account.id,
            local_start_of_day=1111111,
            instant_payout_api=instant_payouts_api,
        )
        expected = PaymentEligibility(
            payout_account_id=created_dx_us_payout_account.id,
            eligible=False,
            reason="payout_pgp_account_not_setup",
            details="The payment external service provider account not setup.",
            balance=None,
            currency=None,
            fee=199,
        )
        assert status == 200
        assert payment_eligibility == expected

        # When submit instant payout now will get 400 bad request error
        instant_payout_create = InstantPayoutCreate(
            payout_account_id=created_dx_us_payout_account.id,
            amount=1111,
            currency="usd",
        )
        with pytest.raises(ApiException) as e:
            submit_instant_payout(
                instant_payout_create=instant_payout_create,
                instant_payout_api=instant_payouts_api,
            )
        assert e.value.status == 400
        body = json.loads(e.value.body)
        assert body.get("error_code") == "invalid_request"
        assert body.get("error_message") == "payout_pgp_account_not_setup"

    def test_not_eligible_due_to_pgp_account_type_not_supported(
        self, created_mx_us_payout_account, instant_payouts_api: InstantPayoutsV1Api
    ):
        # Check eligibility, not eligible due to no pgp account
        payment_eligibility, status, _ = check_instant_payout_eligibility(
            payout_account_id=created_mx_us_payout_account.id,
            local_start_of_day=1111111,
            instant_payout_api=instant_payouts_api,
        )
        expected = PaymentEligibility(
            payout_account_id=created_mx_us_payout_account.id,
            eligible=False,
            reason="payout_account_type_not_supported",
            details="Instant Payout currently only supports Dasher.",
            balance=None,
            currency=None,
            fee=199,
        )
        assert status == 200
        assert payment_eligibility == expected

        # When submit instant payout now will get 400 bad request error
        instant_payout_create = InstantPayoutCreate(
            payout_account_id=created_mx_us_payout_account.id,
            amount=1111,
            currency="usd",
        )
        with pytest.raises(ApiException) as e:
            submit_instant_payout(
                instant_payout_create=instant_payout_create,
                instant_payout_api=instant_payouts_api,
            )
        assert e.value.status == 400
        body = json.loads(e.value.body)
        assert body.get("error_code") == "invalid_request"
        assert body.get("error_message") == "payout_account_type_not_supported"

    @pytest.mark.skip(
        "PaymentAccount and PaymentMethods rollback difference in staging would cause this test flaky."
    )
    def test_not_eligible_due_to_no_payout_card(
        self, verified_dx_us_payout_account, instant_payouts_api: InstantPayoutsV1Api
    ):
        # Check eligibility, not eligible due to no pgp account
        payment_eligibility, status, _ = check_instant_payout_eligibility(
            payout_account_id=verified_dx_us_payout_account.id,
            local_start_of_day=1111111,
            instant_payout_api=instant_payouts_api,
        )
        expected = PaymentEligibility(
            payout_account_id=verified_dx_us_payout_account.id,
            eligible=False,
            reason="payout_card_not_setup",
            details="The payout card is not added yet.",
            balance=None,
            currency=None,
            fee=199,
        )
        assert status == 200
        assert payment_eligibility == expected

        # When submit instant payout now will get 400 bad request error
        instant_payout_create = InstantPayoutCreate(
            payout_account_id=verified_dx_us_payout_account.id,
            amount=1111,
            currency="usd",
        )
        with pytest.raises(ApiException) as e:
            submit_instant_payout(
                instant_payout_create=instant_payout_create,
                instant_payout_api=instant_payouts_api,
            )
        assert e.value.status == 400
        body = json.loads(e.value.body)
        assert body.get("error_code") == "no_default_payout_card"
        assert (
            body.get("error_message")
            == "There is no default payout card for this payout account."
        )

    def test_not_eligible_due_to_amount_mismatch(self):
        # todo: Leon add back more tests when create_payout_method is passed.
        pass
