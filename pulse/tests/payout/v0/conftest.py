import os

import payout_v0_client
import pytest
from payout_v0_client import Configuration

SERVICE_URI = os.getenv("SERVICE_URI", "http://localhost:8082")
API_KEY = os.getenv("API_KEY_PAYMENT_SERVICE", "dummy-key")


def create_client_config() -> Configuration:
    assert SERVICE_URI, "SERVICE_URI is not set"
    config = Configuration(host=SERVICE_URI)

    return config


@pytest.fixture(scope="session")
def client() -> payout_v0_client.ApiClient:
    client_config = create_client_config()
    client = payout_v0_client.ApiClient(client_config)
    client.set_default_header("x-api-key", API_KEY)
    return client
