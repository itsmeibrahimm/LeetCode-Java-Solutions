from datetime import timezone, datetime

import payout_v0_client
import pytest
from payout_v0_client import (
    PaymentAccount,
    PaymentAccountCreate,
    PaymentAccountUpdate,
    NullableString,
    NullableBoolean,
    NullableInteger,
    NullableDatetime,
)

from tests.payout.v0.client_operations import (
    create_payment_account,
    get_payment_account_by_id,
    update_payment_account_by_id,
)


class TestPaymentAccount:
    def test_create_get_update_account_by_id(
        self, accounts_api: payout_v0_client.AccountsV0Api
    ):
        current_time = datetime.now(timezone.utc)
        request = PaymentAccountCreate(
            entity=NullableString(value="dasher"),
            statement_descriptor="pulse-test-statement-descriptor",
            account_id=None,
            account_type=NullableString(value="stripe_managed_account"),
            charges_enabled=NullableBoolean(value=True),
            old_account_id=NullableInteger(value=1234),
            upgraded_to_managed_account_at=NullableDatetime(value=current_time),
            is_verified_with_stripe=NullableBoolean(value=True),
        )

        request_raw = PaymentAccountCreate(
            entity="dasher",
            statement_descriptor="pulse-test-statement-descriptor",
            account_id=None,
            account_type="stripe_managed_account",
            charges_enabled=True,
            old_account_id=1234,
            upgraded_to_managed_account_at=current_time,
            is_verified_with_stripe=True,
        )

        created_account, status, _ = create_payment_account(
            request=request, accounts_api=accounts_api
        )

        assert request_raw.to_dict().items() <= created_account.to_dict().items()
        assert created_account
        assert status == 201

        retrieved_payment_account, status, _ = get_payment_account_by_id(
            payment_account_id=created_account.id, accounts_api=accounts_api
        )
        assert status == 200
        assert isinstance(retrieved_payment_account, PaymentAccount)
        assert retrieved_payment_account == created_account

        updated_payment_account, status, _ = update_payment_account_by_id(
            payment_account_id=retrieved_payment_account.id,
            request=PaymentAccountUpdate(entity=NullableString(value="merchant")),
            accounts_api=accounts_api,
        )

        assert status == 200
        assert updated_payment_account.entity == "merchant"
        assert (
            updated_payment_account.statement_descriptor
            == retrieved_payment_account.statement_descriptor
        )
        assert updated_payment_account.id == retrieved_payment_account.id

        # after change back entity locally, updated payment account should be same as before update
        updated_payment_account.entity = retrieved_payment_account.entity
        assert updated_payment_account == retrieved_payment_account
        print(updated_payment_account)

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
