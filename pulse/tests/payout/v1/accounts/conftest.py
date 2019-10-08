import payout_v1_client
import pytest


@pytest.fixture(scope="session")
def accounts_api(client: payout_v1_client.ApiClient) -> payout_v1_client.AccountsV1Api:
    return payout_v1_client.AccountsV1Api(client)
