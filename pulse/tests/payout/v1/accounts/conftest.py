import pytest


@pytest.fixture(scope="session")
def accounts_api(base_client_pkg, client):
    return base_client_pkg.AccountsV1Api(client)


@pytest.fixture(scope="function")
def versioned_accounts_api(versioned_client_pkg, versioned_client):
    return versioned_client_pkg.AccountsV1Api(versioned_client)
