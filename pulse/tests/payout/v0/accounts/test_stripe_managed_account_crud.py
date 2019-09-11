from datetime import datetime, timezone

import payout_v0_client
import pytest
from payout_v0_client import (
    StripeManagedAccount,
    StripeManagedAccountCreate,
    StripeManagedAccountUpdate,
)

from tests.payout.v0.client_operations import (
    create_stripe_managed_account,
    get_stripe_managed_account_by_id,
    update_stripe_managed_account_by_id,
)


class TestStripeManagedAccount:
    def test_get_account_by_id(self, accounts_api: payout_v0_client.AccountsV0Api):
        request = StripeManagedAccountCreate(
            country_shortname="US",
            stripe_id="pulse-test-stripe-id",
            stripe_last_updated_at=datetime.now(timezone.utc),
            bank_account_last_updated_at=datetime.now(timezone.utc),
            fingerprint="fingerprint",
            verification_disabled_reason="no reason",
            verification_due_by=datetime.now(timezone.utc),
            default_bank_last_four="1234",
            default_bank_name="bank name",
            verification_fields_needed=[],
        )
        created_account, status, _ = create_stripe_managed_account(
            request=request, accounts_api=accounts_api
        )
        assert created_account
        created_dict = created_account.to_dict()
        for k, v in request.to_dict().items():
            if k not in created_dict:
                print("")

        assert status == 201

        retrieved_stripe_managed_account, status, _ = get_stripe_managed_account_by_id(
            stripe_managed_account_id=created_account.id, accounts_api=accounts_api
        )
        assert status == 200
        assert isinstance(retrieved_stripe_managed_account, StripeManagedAccount)
        assert retrieved_stripe_managed_account == created_account

        updated_stripe_managed_account, status, _ = update_stripe_managed_account_by_id(
            stripe_managed_account_id=retrieved_stripe_managed_account.id,
            request=StripeManagedAccountUpdate(country_shortname="CA"),
            accounts_api=accounts_api,
        )

        assert status == 200
        assert updated_stripe_managed_account.id == retrieved_stripe_managed_account.id
        assert updated_stripe_managed_account.country_shortname == "CA"
        assert (
            updated_stripe_managed_account.stripe_id
            == retrieved_stripe_managed_account.stripe_id
        )

        # after set back country_shortname locally, updated should be same as previously retrived before update
        updated_stripe_managed_account.country_shortname = (
            retrieved_stripe_managed_account.country_shortname
        )
        assert updated_stripe_managed_account == retrieved_stripe_managed_account

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
