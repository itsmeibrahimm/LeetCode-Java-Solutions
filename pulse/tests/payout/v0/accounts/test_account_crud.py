import payout_v0_client

from tests.payout.v0.client_operations import get_payment_account_by_id
from payout_v0_client import PaymentAccount


def test_get_account_by_id(
    payment_account_readonly: PaymentAccount,
    accounts_api: payout_v0_client.AccountsV0Api,
):
    retrieved_payment_account, _, _ = get_payment_account_by_id(
        payment_account_id=payment_account_readonly.id, accounts_api=accounts_api
    )
    assert isinstance(retrieved_payment_account, PaymentAccount)
    assert retrieved_payment_account == payment_account_readonly
