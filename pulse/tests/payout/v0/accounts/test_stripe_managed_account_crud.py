import payout_v0_client
import pytest
from payout_v0_client import StripeManagedAccount, StripeManagedAccountCreate

from tests.payout.v0.client_operations import (
    create_stripe_managed_account,
    get_stripe_managed_account_by_id,
)


class TestStripeManagedAccount:
    def test_get_account_by_id(self, accounts_api: payout_v0_client.AccountsV0Api):
        request = StripeManagedAccountCreate(
            country_shortname="US", stripe_id="pulse-test-stripe-id"
        )
        created_account, status, _ = create_stripe_managed_account(
            request=request, accounts_api=accounts_api
        )
        assert created_account
        assert status == 201

        retrieved_stripe_managed_account, status, _ = get_stripe_managed_account_by_id(
            stripe_managed_account_id=created_account.id, accounts_api=accounts_api
        )
        assert status == 200
        assert isinstance(retrieved_stripe_managed_account, StripeManagedAccount)
        assert retrieved_stripe_managed_account == created_account

    @pytest.mark.run_in_prod_only
    def test_get_prod_account(self, accounts_api: payout_v0_client.AccountsV0Api):
        prod_test_stripe_managed_account_id = (
            780484
        )  # frosty bear: https://internal.doordash.com/payments/transfers/?payment_account_id=717514
        retrieved_stripe_managed_account, status, _ = get_stripe_managed_account_by_id(
            stripe_managed_account_id=prod_test_stripe_managed_account_id,
            accounts_api=accounts_api,
        )
        assert status == 200
        assert isinstance(retrieved_stripe_managed_account, StripeManagedAccount)
        assert (
            retrieved_stripe_managed_account.id == prod_test_stripe_managed_account_id
        )
