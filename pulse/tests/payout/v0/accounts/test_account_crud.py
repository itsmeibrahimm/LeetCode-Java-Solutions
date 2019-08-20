import payout_v0_client
import pytest
from payout_v0_client import PaymentAccount, PaymentAccountCreate

from tests.payout.v0.client_operations import (
    create_payment_account,
    get_payment_account_by_id,
)


class TestPaymentAccount:
    def test_get_account_by_id(self, accounts_api: payout_v0_client.AccountsV0Api):
        request = PaymentAccountCreate(
            entity="dasher", statement_descriptor="pulse-test-statement-descriptor"
        )

        created_account, status, _ = create_payment_account(
            request=request, accounts_api=accounts_api
        )
        assert created_account
        assert status == 201

        retrieved_payment_account, status, _ = get_payment_account_by_id(
            payment_account_id=created_account.id, accounts_api=accounts_api
        )
        assert status == 200
        assert isinstance(retrieved_payment_account, PaymentAccount)
        assert retrieved_payment_account == created_account

    @pytest.mark.run_in_prod_only
    def test_get_prod_account(self, accounts_api: payout_v0_client.AccountsV0Api):
        prod_test_account_id = (
            717514
        )  # frosty bear: https://internal.doordash.com/payments/transfers/?payment_account_id=717514
        retrieved_payment_account, status, _ = get_payment_account_by_id(
            payment_account_id=prod_test_account_id, accounts_api=accounts_api
        )
        assert status == 200
        assert isinstance(retrieved_payment_account, PaymentAccount)
        assert retrieved_payment_account.id == prod_test_account_id
