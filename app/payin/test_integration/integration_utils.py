from uuid import UUID

from pydantic import BaseModel
from starlette.testclient import TestClient
from typing import Any, Dict, Optional

V1_PAYERS_ENDPOINT = "/payin/api/v1/payers"
V0_PAYMENT_METHODS_ENDPOINT = "/payin/api/v0/payment_methods"
V1_PAYMENT_METHODS_ENDPOINT = "/payin/api/v1/payment_methods"


class CreatePayerV1Request(BaseModel):
    dd_payer_id: Optional[str]
    payer_type: Optional[str]
    email: Optional[str]
    country: Optional[str]
    description: Optional[str]


class CreatePaymentMethodV1Request(BaseModel):
    payer_id: str
    payment_gateway: str
    token: str


class PayinError(BaseModel):
    http_status_code: int
    error_code: str
    retryable: bool


def _create_payer_v1_url():
    return V1_PAYERS_ENDPOINT


def _create_payment_method_v0_url():
    return V0_PAYMENT_METHODS_ENDPOINT


def _create_payment_method_v1_url():
    return V1_PAYMENT_METHODS_ENDPOINT


def _delete_payment_methods_url(payment_method_id: str):
    return f"{V1_PAYMENT_METHODS_ENDPOINT}/{payment_method_id}"


def create_payer_v1(
    client: TestClient, request: CreatePayerV1Request
) -> Dict[str, Any]:
    create_payer_request = {
        # FIXME: PAY-3773 re-enforce dd_payer_id when the consumer_id constraint in maindb.stripe_card is removed.
        # "dd_payer_id": request.dd_payer_id,
        "payer_type": request.payer_type,
        "email": request.email,
        "country": request.country,
        "description": request.description,
    }
    response = client.post(_create_payer_v1_url(), json=create_payer_request)
    assert response.status_code == 201
    payer: dict = response.json()
    assert UUID(payer["id"], version=4)
    # FIXME: PAY-3773 re-enforce dd_payer_id when the consumer_id constraint in maindb.stripe_card is removed.
    # assert payer["dd_payer_id"] == request.dd_payer_id
    assert payer["country"] == request.country
    assert payer["description"] == request.description
    assert payer["payer_type"] == request.payer_type
    assert (
        payer["payment_gateway_provider_customers"][0]["payment_provider"] == "stripe"
    )
    assert (
        payer["payment_gateway_provider_customers"][0]["payment_provider_customer_id"]
        is not None
    )
    assert (
        payer["payment_gateway_provider_customers"][0]["default_payment_method_id"]
        is None
    )

    return payer


def create_payer_failure_v1(
    client: TestClient, request: CreatePayerV1Request, error: PayinError
):
    create_payer_request = {
        "dd_payer_id": request.dd_payer_id,
        "payer_type": request.payer_type,
        "email": request.email,
        "country": request.country,
        "description": request.description,
    }
    response = client.post(_create_payer_v1_url(), json=create_payer_request)
    assert response.status_code == error.http_status_code
    error_response: dict = response.json()
    assert error_response["error_code"] == error.error_code
    assert error_response["retryable"] == error.retryable


def create_payment_method_v1(
    client: TestClient,
    request: CreatePaymentMethodV1Request,
    http_status: Optional[int] = 201,
) -> Dict[str, Any]:
    create_payment_method_request = {
        "payer_id": request.payer_id,
        "payment_gateway": request.payment_gateway,
        "token": request.token,
    }
    response = client.post(
        _create_payment_method_v1_url(), json=create_payment_method_request
    )
    assert response.status_code == http_status
    payment_method: dict = response.json()
    assert UUID(payment_method["id"], version=4)
    assert UUID(payment_method["payer_id"], version=4)
    assert payment_method["dd_stripe_card_id"]
    assert payment_method["created_at"]
    assert payment_method["updated_at"]
    assert payment_method["created_at"] == payment_method["updated_at"]
    assert payment_method["deleted_at"] is None
    assert payment_method["type"] == "card"
    assert (
        payment_method["payment_gateway_provider_details"]["payment_provider"]
        == "stripe"
    )
    assert (
        payment_method["payment_gateway_provider_details"]["payment_method_id"]
        is not None
    )
    assert payment_method["payment_gateway_provider_details"]["customer_id"] is not None
    assert payment_method["card"]["last4"] is not None
    assert payment_method["card"]["exp_year"] is not None
    assert payment_method["card"]["exp_month"] is not None
    assert payment_method["card"]["fingerprint"] is not None
    # FIXME: PAY-3773 re-enforce dd_payer_id when the consumer_id constraint in maindb.stripe_card is removed.
    # assert payment_method["dd_payer_id"] is not None
    return payment_method


def delete_payment_methods_v1(
    client: TestClient, payment_method_id: Any
) -> Dict[str, Any]:
    response = client.delete(
        _delete_payment_methods_url(payment_method_id=payment_method_id)
    )
    assert response.status_code == 200
    payment_method: dict = response.json()
    assert payment_method["deleted_at"] is not None
    return payment_method
