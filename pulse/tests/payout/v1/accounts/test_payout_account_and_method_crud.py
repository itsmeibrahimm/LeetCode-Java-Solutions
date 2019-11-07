from copy import deepcopy
import pytest
import uuid
import stripe
from payout_v1_client import (
    ApiException,
    AccountsV1Api,
    CreatePayoutAccount,
    VerificationDetailsWithToken,
    CreatePayoutMethod,
    PayoutAccount,
    PayoutMethodCard,
)

from tests.payout.v1.client_operations import (
    create_payout_account,
    verify_payout_account_legacy,
    create_payout_method,
    get_payout_account,
    update_payout_account_statement_descriptor,
    get_payout_method,
    list_payout_method,
)

# Use Stripe public key to create account token
STRIPE_US_PUBLIC_API_KEY = "pk_test_VCKL0VKIMMPzuUB8ZbuXdKkA"


class TestPayoutAccount:
    base_account_create_request = CreatePayoutAccount(
        target_id=12345,
        target_type="store",
        country="US",
        currency="usd",
        statement_descriptor="pulse-test-statement-descriptor",
    )

    async def test_create_payout_account_success(
        self, accounts_api: AccountsV1Api
    ) -> int:
        # Test with creating payout account successfully
        created_payout_account, status, _ = create_payout_account(
            request=self.base_account_create_request, accounts_api=accounts_api
        )
        assert created_payout_account
        assert created_payout_account.id
        assert (
            created_payout_account.statement_descriptor
            == "pulse-test-statement-descriptor"
        )
        assert created_payout_account.pgp_account_id is None
        assert created_payout_account.pgp_external_account_id is None
        assert status == 201
        return created_payout_account.id

    async def test_retrieve_payout_account_success(self, accounts_api: AccountsV1Api):
        # Test with retrieving payout account by id successfully
        payout_account_id = await self.test_create_payout_account_success(
            accounts_api=accounts_api
        )
        retrieved_payout_account, status, _ = get_payout_account(
            payout_account_id=payout_account_id, accounts_api=accounts_api
        )
        assert status == 200
        assert isinstance(retrieved_payout_account, PayoutAccount)
        assert retrieved_payout_account.id == payout_account_id

    async def test_update_payout_account_statement_descriptor_success(
        self, accounts_api: AccountsV1Api
    ):
        # Test with updating payout account statement descriptor by id successfully
        payout_account_id = await self.test_create_payout_account_success(
            accounts_api=accounts_api
        )
        updated_payout_account, status, _ = update_payout_account_statement_descriptor(
            payout_account_id=payout_account_id,
            statement_descriptor="updated statement_descriptor",
            accounts_api=accounts_api,
        )
        assert status == 200
        assert (
            updated_payout_account.statement_descriptor
            == "updated statement_descriptor"
        )
        assert updated_payout_account.id == payout_account_id

    async def test_verify_and_update_payout_account_success(
        self, accounts_api: AccountsV1Api
    ) -> int:
        # Test with verifying payout account with account token
        payout_account_id = await self.test_create_payout_account_success(
            accounts_api=accounts_api
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
            payout_account_id=payout_account_id,
            verification_details_with_token=verification_details_with_token,
            accounts_api=accounts_api,
        )
        assert verified_payout_account
        assert status == 200
        assert verified_payout_account.pgp_account_id
        assert verified_payout_account.pgp_external_account_id
        assert verified_payout_account.pgp_account_type

        # Test with updating stripe account kyc info of an existing account
        account_token = stripe.Token.create(
            account={
                "business_type": "individual",
                "individual": {"first_name": "David", "last_name": "Doe"},
                "tos_shown_and_accepted": True,
            }
        )
        verification_details_with_token = VerificationDetailsWithToken(
            account_token=account_token.get("id"), country="US", currency="usd"
        )

        updated_payout_account, status, _ = verify_payout_account_legacy(
            payout_account_id=payout_account_id,
            verification_details_with_token=verification_details_with_token,
            accounts_api=accounts_api,
        )
        # TODO: Fetch Stripe account to verify the updated info
        assert updated_payout_account
        assert status == 200

        return updated_payout_account.id

    async def test_create_and_retrieve_payout_method_success(
        self, accounts_api: AccountsV1Api
    ):
        # Test with creating payout method with payout account id
        payout_account_id = await self.test_verify_and_update_payout_account_success(
            accounts_api
        )
        payout_method_request = CreatePayoutMethod(token="tok_visa_debit", type="card")
        created_payout_method, status, _ = create_payout_method(
            payout_account_id=payout_account_id,
            request=payout_method_request,
            accounts_api=accounts_api,
        )
        assert created_payout_method
        assert created_payout_method.type == "card"
        assert created_payout_method.brand == "Visa"
        assert created_payout_method.fingerprint
        assert status == 201

        # Test with retrieving payout method by payout account id and payout method id
        retrieved_payout_method, status, _ = get_payout_method(
            payout_account_id=payout_account_id,
            payout_method_id=created_payout_method.id,
            accounts_api=accounts_api,
        )
        assert status == 200
        assert isinstance(retrieved_payout_method, PayoutMethodCard)
        assert retrieved_payout_method == created_payout_method

        # Test with listing payout methods by payout account id
        created_payout_method_1, status, _ = create_payout_method(
            payout_account_id=payout_account_id,
            request=payout_method_request,
            accounts_api=accounts_api,
        )
        created_payout_method_2, status, _ = create_payout_method(
            payout_account_id=payout_account_id,
            request=payout_method_request,
            accounts_api=accounts_api,
        )
        payout_method_list, status, _ = list_payout_method(
            payout_account_id=payout_account_id, accounts_api=accounts_api
        )
        assert status == 200
        assert payout_method_list.count == 3
        assert isinstance(payout_method_list.card_list[0], PayoutMethodCard)
        assert created_payout_method.id == payout_method_list.card_list[2].id
        assert created_payout_method_2.id == payout_method_list.card_list[0].id
        assert payout_method_list.card_list[0].is_default is True
        assert payout_method_list.card_list[1].is_default is False
        assert payout_method_list.card_list[2].is_default is False

    def test_create_payout_account_malformed(self, accounts_api: AccountsV1Api):
        # Test with invalid country
        request = deepcopy(self.base_account_create_request)
        with pytest.raises(ValueError):
            request.country = "something"
            create_payout_account(request=request, accounts_api=accounts_api)

        # Test with invalid currency
        request = deepcopy(self.base_account_create_request)
        with pytest.raises(ValueError):
            request.currency = "something"
            create_payout_account(request=request, accounts_api=accounts_api)

        # Test with invalid target type
        request = deepcopy(self.base_account_create_request)
        with pytest.raises(ValueError):
            request.target_type = "something"
            create_payout_account(request=request, accounts_api=accounts_api)

    def test_get_payout_account_malformed(self, accounts_api: AccountsV1Api):
        payout_account_id = 123456789
        with pytest.raises(ApiException):
            get_payout_account(
                payout_account_id=payout_account_id, accounts_api=accounts_api
            )

    def test_update_payout_account_malformed(self, accounts_api: AccountsV1Api):
        payout_account_id = 123456789
        with pytest.raises(ApiException):
            update_payout_account_statement_descriptor(
                payout_account_id=payout_account_id,
                statement_descriptor="updated statement_descriptor",
                accounts_api=accounts_api,
            )

    def test_verification_payout_account_malformed(self, accounts_api: AccountsV1Api):
        # Test with invalid payout account id
        payout_account_id = 123456789
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
        with pytest.raises(ApiException):
            verify_payout_account_legacy(
                payout_account_id=payout_account_id,
                verification_details_with_token=verification_details_with_token,
                accounts_api=accounts_api,
            )

        created_payout_account, status, _ = create_payout_account(
            request=self.base_account_create_request, accounts_api=accounts_api
        )

        # Test with invalid country
        with pytest.raises(ValueError):
            verification_details_with_token_invalid_country = VerificationDetailsWithToken(
                account_token=account_token.get("id"),
                country="something",
                currency="usd",
            )
            verify_payout_account_legacy(
                payout_account_id=created_payout_account.id,
                verification_details_with_token=verification_details_with_token_invalid_country,
                accounts_api=accounts_api,
            )

        # Test with invalid currency
        with pytest.raises(ValueError):
            verification_details_with_token_invalid_country = VerificationDetailsWithToken(
                account_token=account_token.get("id"),
                country="US",
                currency="something",
            )
            verify_payout_account_legacy(
                payout_account_id=created_payout_account.id,
                verification_details_with_token=verification_details_with_token_invalid_country,
                accounts_api=accounts_api,
            )

        # Test with mismatch country and currency
        with pytest.raises(ApiException):
            verification_details_with_token_invalid_country = VerificationDetailsWithToken(
                account_token=account_token.get("id"), country="AU", currency="usd"
            )
            verify_payout_account_legacy(
                payout_account_id=created_payout_account.id,
                verification_details_with_token=verification_details_with_token_invalid_country,
                accounts_api=accounts_api,
            )

        # Test with invalid account_token
        account_token = str(uuid.uuid4())
        verification_details_with_token = VerificationDetailsWithToken(
            account_token=account_token, country="US", currency="usd"
        )
        with pytest.raises(ApiException):
            verify_payout_account_legacy(
                payout_account_id=created_payout_account.id,
                verification_details_with_token=verification_details_with_token,
                accounts_api=accounts_api,
            )

    def test_verification_payout_account_with_used_token(
        self, accounts_api: AccountsV1Api
    ):
        created_payout_account, status, _ = create_payout_account(
            request=self.base_account_create_request, accounts_api=accounts_api
        )
        account_token_dup = stripe.Token.create(
            account={
                "business_type": "individual",
                "individual": {"first_name": "David", "last_name": "Doe"},
                "tos_shown_and_accepted": True,
            }
        )
        verification_details_with_token = VerificationDetailsWithToken(
            account_token=account_token_dup.get("id"), country="US", currency="usd"
        )
        verify_payout_account_legacy(
            payout_account_id=created_payout_account.id,
            verification_details_with_token=verification_details_with_token,
            accounts_api=accounts_api,
        )
        # Reuse the used account token
        verification_details_with_token_dup = VerificationDetailsWithToken(
            account_token=account_token_dup.get("id"), country="US", currency="usd"
        )
        with pytest.raises(ApiException):
            verify_payout_account_legacy(
                payout_account_id=created_payout_account.id,
                verification_details_with_token=verification_details_with_token_dup,
                accounts_api=accounts_api,
            )

    def test_create_payout_method_malformed(self, accounts_api: AccountsV1Api):
        # Test with invalid payout account id
        payout_account_id = 123456789
        payout_method_request = CreatePayoutMethod(token="tok_visa_debit", type="card")

        with pytest.raises(ApiException):
            create_payout_method(
                payout_account_id=payout_account_id,
                request=payout_method_request,
                accounts_api=accounts_api,
            )

        # Test with valid payout account id but without verification (e.g., sma related setup)
        created_payout_account, status, _ = create_payout_account(
            request=self.base_account_create_request, accounts_api=accounts_api
        )
        with pytest.raises(ApiException):
            create_payout_method(
                payout_account_id=created_payout_account.id,
                request=payout_method_request,
                accounts_api=accounts_api,
            )

    def test_common_workflow(
        self, versioned_client_pkg, versioned_accounts_api: AccountsV1Api
    ):
        # any workflow that should not be broken for all versions
        assert versioned_client_pkg.__version__ in ["0.0.8", "0.0.9"]
