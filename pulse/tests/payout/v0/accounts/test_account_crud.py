from copy import deepcopy
from datetime import datetime, timezone

import payout_v0_client
import pytest
from payout_v0_client import (
    PaymentAccount,
    PaymentAccountCreate,
    PaymentAccountUpdate,
    ApiException,
)

from tests.payout.v0.client_operations import (
    create_payment_account,
    get_payment_account_by_id,
    update_payment_account_by_id,
)


class TestPaymentAccount:

    base_account_create = PaymentAccountCreate(
        statement_descriptor="pulse-test-statement-descriptor",
        account_id=123,
        account_type="stripe_managed_account",
        entity="dasher",
        resolve_outstanding_balance_frequency="daily",
        payout_disabled=True,
        charges_enabled=True,
        old_account_id=123,
        upgraded_to_managed_account_at=datetime.now(timezone.utc),
        is_verified_with_stripe=True,
        transfers_enabled=True,
    )

    def test_create_get_update_account_by_id(
        self, accounts_api: payout_v0_client.AccountsV0Api
    ):
        request = self.base_account_create

        created_account, status, _ = create_payment_account(
            request=request, accounts_api=accounts_api
        )
        assert request.to_dict().items() <= created_account.to_dict().items()
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
            request=PaymentAccountUpdate(entity="merchant"),
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

        # Update not null field (use entity here) should succeed
        # Need to construct a dict in order to pass None value to client
        payment_account_update = {"entity": None}
        updated_payment_account, status, _ = accounts_api.update_payment_account_by_id_with_http_info(
            retrieved_payment_account.id, payment_account_update
        )

        assert updated_payment_account.entity is None

        retrieved_payment_account, status, _ = get_payment_account_by_id(
            payment_account_id=created_account.id, accounts_api=accounts_api
        )
        assert retrieved_payment_account == updated_payment_account

        # Update statement_descriptor to Null value should raise ApiException.
        # Need to construct a dict in order to pass None value to client
        payment_account_update = {"statement_descriptor": None}
        with pytest.raises(ApiException):
            accounts_api.update_payment_account_by_id_with_http_info(
                retrieved_payment_account.id, payment_account_update
            )

        # Update statement_descriptor to Null value along with other field should also raise ApiException.
        payment_account_update = {
            "statement_descriptor": None,
            "payout_disabled": False,
        }
        with pytest.raises(Exception):
            accounts_api.update_payment_account_by_id_with_http_info(
                retrieved_payment_account.id, payment_account_update
            )

    def test_create_account_malformed(
        self, accounts_api: payout_v0_client.AccountsV0Api
    ):
        request = deepcopy(self.base_account_create)
        with pytest.raises(Exception) as e:
            request.account_type = "somethingelse"
        assert e.type == ValueError

        request = deepcopy(self.base_account_create)
        with pytest.raises(Exception) as e:
            request.entity = "somethingelse"
        assert e.type == ValueError

        request = deepcopy(self.base_account_create)
        with pytest.raises(Exception) as e:
            request.resolve_outstanding_balance_frequency = "somethingelse"
        assert e.type == ValueError

    def test_update_account_malformed(
        self, accounts_api: payout_v0_client.AccountsV0Api
    ):
        with pytest.raises(Exception) as e:
            PaymentAccountUpdate(account_type="somethingelse")
        assert e.type == ValueError

        with pytest.raises(Exception) as e:
            PaymentAccountUpdate(entity="somethingelse")
        assert e.type == ValueError

        with pytest.raises(Exception) as e:
            PaymentAccountUpdate(resolve_outstanding_balance_frequency="somethingelse")
        assert e.type == ValueError

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
