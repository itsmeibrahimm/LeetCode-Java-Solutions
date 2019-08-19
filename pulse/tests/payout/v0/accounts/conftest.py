import payout_v0_client
import pytest
from payout_v0_client import (
    PaymentAccount,
    PaymentAccountCreate,
    StripeManagedAccount,
    StripeManagedAccountCreate,
)
from tests.payout.v0.client_operations import (
    create_payment_account,
    create_stripe_managed_account,
)


@pytest.fixture(scope="session")
def accounts_api(client: payout_v0_client.ApiClient) -> payout_v0_client.AccountsV0Api:
    return payout_v0_client.AccountsV0Api(client)


@pytest.fixture(scope="session")
def payment_account_readonly(
    accounts_api: payout_v0_client.AccountsV0Api
) -> PaymentAccount:
    request = PaymentAccountCreate(
        entity="dasher", statement_descriptor="pulse-test-statement-descriptor"
    )

    account, status, _ = create_payment_account(
        request=request, accounts_api=accounts_api
    )
    assert account
    assert status == 201
    return account


@pytest.fixture(scope="session")
def stripe_managed_account_readonly(
    accounts_api: payout_v0_client.AccountsV0Api
) -> StripeManagedAccount:
    request = StripeManagedAccountCreate(
        country_shortname="US", stripe_id="pulse-test-stripe-id"
    )
    account, status, _ = create_stripe_managed_account(
        request=request, accounts_api=accounts_api
    )
    assert account
    assert status == 201
    return account
