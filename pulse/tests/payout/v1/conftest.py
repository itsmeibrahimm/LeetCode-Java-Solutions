import os
import pytest
from tests.utils import reload_pkg_version

#######################
# TEST CLIENT CONFIGS #
#######################
SERVICE_URI = os.getenv("SERVICE_URI", "http://localhost:8182")
API_KEY = os.getenv("API_KEY_PAYMENT_SERVICE", "dummy-key")
BASE_CLIENT_VERSION = "0.0.11"
EXTRA_CLIENT_VERSIONS = []


@pytest.fixture(scope="session")
def base_client_pkg():
    v1_client_pkg = reload_pkg_version(
        "payout-v1-client", "payout_v1_client", BASE_CLIENT_VERSION
    )
    assert v1_client_pkg.__version__ == BASE_CLIENT_VERSION
    return v1_client_pkg


@pytest.fixture(scope="session")
def client(base_client_pkg):
    client_config = base_client_pkg.Configuration(host=SERVICE_URI)

    client = base_client_pkg.ApiClient(client_config)
    client.set_default_header("x-api-key", API_KEY)
    return client


def pytest_generate_tests(metafunc):
    if "versioned_client_pkg" in metafunc.fixturenames:
        metafunc.parametrize(
            "versioned_client_pkg", EXTRA_CLIENT_VERSIONS, indirect=True
        )


@pytest.yield_fixture
def versioned_client_pkg(request):
    v1_client_pkg = reload_pkg_version(
        "payout-v1-client", "payout_v1_client", request.param
    )
    assert v1_client_pkg.__version__ == request.param
    yield v1_client_pkg
    reload_pkg_version("payout-v1-client", "payout_v1_client", BASE_CLIENT_VERSION)


@pytest.yield_fixture
def versioned_client(versioned_client_pkg):
    client_config = versioned_client_pkg.Configuration(host=SERVICE_URI)
    client = versioned_client_pkg.ApiClient(client_config)
    client.set_default_header("x-api-key", API_KEY)
    yield client
