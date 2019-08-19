import payout_v0_client
from payout_v0_client import StripeManagedAccount

from tests.payout.v0.client_operations import get_stripe_managed_account_by_id


def test_get_account_by_id(
    stripe_managed_account_readonly: StripeManagedAccount,
    accounts_api: payout_v0_client.AccountsV0Api,
):
    retrieved_stripe_managed_account, _, _ = get_stripe_managed_account_by_id(
        stripe_managed_account_id=stripe_managed_account_readonly.id,
        accounts_api=accounts_api,
    )
    assert isinstance(retrieved_stripe_managed_account, StripeManagedAccount)
    assert retrieved_stripe_managed_account == stripe_managed_account_readonly
