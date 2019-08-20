import payout_v0_client
import pytest


@pytest.fixture(scope="session")
def accounts_api(client: payout_v0_client.ApiClient) -> payout_v0_client.AccountsV0Api:
    return payout_v0_client.AccountsV0Api(client)
