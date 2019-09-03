import pytest
from starlette.testclient import TestClient

from app.commons.constants import PAYMENT_REQUEST_ID_HEADER


def test_req_id_in_success_response(client: TestClient):
    response = client.get("/health")
    assert PAYMENT_REQUEST_ID_HEADER in response.headers


def test_req_id_in_invalid_path_repsonse(client: TestClient):
    response = client.get("/health/123")
    assert response.status_code == 404  # expected path not found
    assert PAYMENT_REQUEST_ID_HEADER in response.headers


def test_req_id_in_validation_error_response(client: TestClient):
    response = client.post(
        "/payout/api/v0/accounts/",
        json={
            "account_id": "unexpectedstring",
            "account_type": "string",
            "entity": "string",
            "resolve_outstanding_balance_frequency": "string",
            "payout_disabled": True,
            "charges_enabled": True,
            "old_account_id": 0,
            "upgraded_to_managed_account_at": "2019-09-03T17:22:08.695Z",
            "is_verified_with_stripe": True,
            "transfers_enabled": True,
            "statement_descriptor": "string",
        },
    )
    assert response.status_code == 422  # expected validation error
    assert PAYMENT_REQUEST_ID_HEADER in response.headers


@pytest.mark.skip(
    "test client doesn't run all middlewares, but this is working in actual application"
)
def test_req_id_in_internal_error_response(client: TestClient):
    response = client.get("/error")
    assert response.status_code == 500  # expected internal server error
    assert PAYMENT_REQUEST_ID_HEADER in response.headers
