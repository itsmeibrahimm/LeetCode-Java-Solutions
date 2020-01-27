from uuid import UUID

from pydantic import BaseModel
from starlette.testclient import TestClient
from typing import Any, Dict, Optional

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.commons.types import CountryCode
from app.payin.core.cart_payment.commando_mode_processor import CommandoProcessor
from app.payin.core.cart_payment.cart_payment_client import CartPaymentInterface
from app.payin.core.cart_payment.legacy_cart_payment_client import (
    LegacyPaymentInterface,
)
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.core.payment_method.types import PaymentMethodSortKey
from app.payin.core.types import PayerReferenceIdType
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository

V1_PAYERS_ENDPOINT = "/payin/api/v1/payers"
V0_PAYMENT_METHODS_ENDPOINT = "/payin/api/v0/payment_methods"
V1_PAYMENT_METHODS_ENDPOINT = "/payin/api/v1/payment_methods"


class CreatePayerV1Request(BaseModel):
    payer_reference_id: Optional[str]
    payer_reference_id_type: Optional[str]
    email: Optional[str]
    country: Optional[str]
    description: Optional[str]


class CreatePaymentMethodV0Request(BaseModel):
    token: str
    country: str
    stripe_customer_id: str
    set_default: bool
    is_scanned: bool
    is_active: bool
    payer_type: Optional[str]
    dd_consumer_id: Optional[str]
    legacy_dd_stripe_customer_id: Optional[str]


class CreatePaymentMethodV1Request(BaseModel):
    payer_id: Optional[str] = None
    payer_reference_id: Optional[str] = None
    payer_reference_id_type: Optional[str] = None
    payment_gateway: str
    token: str
    set_default: bool
    is_scanned: bool
    is_active: bool
    create_payer_request: Optional[CreatePayerV1Request] = None


class PayinError(BaseModel):
    http_status_code: int
    error_code: str
    retryable: bool


def _create_payer_v1_url():
    return V1_PAYERS_ENDPOINT


def _create_payment_method_v0_url():
    return V0_PAYMENT_METHODS_ENDPOINT


def _delete_payment_method_v0_url(payment_method_id_type: str, payment_method_id: str):
    return f"{V0_PAYMENT_METHODS_ENDPOINT}/{payment_method_id_type}/{payment_method_id}"


def _create_payment_method_v1_url():
    return V1_PAYMENT_METHODS_ENDPOINT


def _delete_payment_method_v1_url(payment_method_id: str):
    return f"{V1_PAYMENT_METHODS_ENDPOINT}/{payment_method_id}"


def _list_payment_method_v1_url(
    active_only: bool = False,
    sort_by: PaymentMethodSortKey = PaymentMethodSortKey.CREATED_AT,
    force_update: bool = None,
    country: CountryCode = None,
    payer_id: Optional[str] = None,
    payer_reference_id: Optional[str] = None,
    payer_reference_id_type: Optional[str] = None,
):
    base_request = (
        f"{V1_PAYMENT_METHODS_ENDPOINT}?active_only={active_only}&sort_by={sort_by}"
    )
    if force_update:
        base_request = base_request + f"&force_update={force_update}"
    if country:
        base_request = base_request + f"&country={country}"
    if payer_id:
        base_request = base_request + f"&payer_id={payer_id}"
    if payer_reference_id:
        base_request = base_request + f"&payer_reference_id={payer_reference_id}"
    if payer_reference_id_type:
        base_request = (
            base_request + f"&payer_reference_id_type={payer_reference_id_type}"
        )
    return base_request


def create_payer_v1(
    client: TestClient, request: CreatePayerV1Request, duplicate_request: bool = False
) -> Dict[str, Any]:
    create_payer_request = {
        "payer_correlation_ids": {
            "payer_reference_id": request.payer_reference_id,
            "payer_reference_id_type": request.payer_reference_id_type,
        },
        "email": request.email,
        "country": request.country,
        "description": request.description,
    }
    response = client.post(_create_payer_v1_url(), json=create_payer_request)
    assert response.status_code in (201, 200)
    if duplicate_request:
        assert response.status_code == 200
    payer: dict = response.json()
    assert UUID(payer["id"], version=4)
    assert payer["country"] == request.country
    assert payer["description"] == request.description
    assert payer["created_at"]
    assert payer["updated_at"]
    assert payer["deleted_at"] is None
    if request.payer_reference_id_type == "dd_consumer_id":
        assert payer["legacy_dd_stripe_customer_id"] is None
    else:
        assert payer["legacy_dd_stripe_customer_id"] is not None
    assert (
        payer["payer_correlation_ids"]["payer_reference_id"]
        == request.payer_reference_id
    )
    assert (
        payer["payer_correlation_ids"]["payer_reference_id_type"]
        == request.payer_reference_id_type
    )
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
    if request.payer_reference_id_type in (
        PayerReferenceIdType.DD_DRIVE_BUSINESS_ID,
        PayerReferenceIdType.DD_DRIVE_STORE_ID,
        PayerReferenceIdType.DD_DRIVE_MERCHANT_ID,
    ):
        assert "legacy_dd_stripe_customer_id" in payer
        assert payer["legacy_dd_stripe_customer_id"]

    return payer


def create_payer_failure_v1(
    client: TestClient, request: CreatePayerV1Request, error: PayinError
):
    create_payer_request = {
        "payer_correlation_ids": {
            "payer_reference_id": request.payer_reference_id,
            "payer_reference_id_type": request.payer_reference_id_type,
        },
        "email": request.email,
        "country": request.country,
        "description": request.description,
    }
    response = client.post(_create_payer_v1_url(), json=create_payer_request)
    assert response.status_code == error.http_status_code
    error_response: dict = response.json()
    assert error_response["error_code"] == error.error_code
    assert error_response["retryable"] == error.retryable


def create_payment_method_v0(
    client: TestClient,
    request: CreatePaymentMethodV0Request,
    http_status: Optional[int] = 201,
) -> Dict[str, Any]:
    create_payment_method_request = {
        "stripe_customer_id": request.stripe_customer_id,
        "token": request.token,
        "country": request.country,
        "set_default": request.set_default,
        "is_active": request.is_active,
        "is_scanned": request.is_scanned,
    }
    if request.dd_consumer_id:
        create_payment_method_request.update(
            {"dd_consumer_id": str(request.dd_consumer_id)}
        )
    if request.legacy_dd_stripe_customer_id:
        create_payment_method_request.update(
            {"legacy_dd_stripe_customer_id": str(request.legacy_dd_stripe_customer_id)}
        )
    if request.payer_type:
        create_payment_method_request.update({"payer_type": str(request.payer_type)})
    response = client.post(
        _create_payment_method_v0_url(), json=create_payment_method_request
    )
    assert response.status_code == http_status
    payment_method: dict = response.json()
    assert UUID(payment_method["id"], version=4)
    # payer_id could be None if payer doesnt't exist and lazy creation is disabled.
    # assert UUID(payment_method["payer_id"], version=4)
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
    # assert payment_method["dd_payer_id"] is not None
    return payment_method


def delete_payment_methods_v0(
    client: TestClient, payment_method_id_type: Any, payment_method_id: Any
) -> Dict[str, Any]:
    response = client.delete(
        _delete_payment_method_v0_url(
            payment_method_id_type=payment_method_id_type,
            payment_method_id=payment_method_id,
        )
        + "?country=US"
    )
    assert response.status_code == 200
    payment_method: dict = response.json()
    assert payment_method["deleted_at"] is not None
    return payment_method


def create_payment_method_v1(
    client: TestClient,
    request: CreatePaymentMethodV1Request,
    http_status: Optional[int] = 201,
) -> Dict[str, Any]:
    create_payment_method_request: Dict[str, Any] = {
        "payer_id": request.payer_id,
        "payment_gateway": request.payment_gateway,
        "token": request.token,
        "set_default": request.set_default,
        "is_active": request.is_active,
        "is_scanned": request.is_scanned,
        "create_payer_request": request.create_payer_request,
    }
    if request.payer_id:
        create_payment_method_request.update({"payer_id": request.payer_id})
    if request.payer_reference_id and request.payer_reference_id_type:
        payer_correlation_ids = {
            "payer_reference_id": request.payer_reference_id,
            "payer_reference_id_type": request.payer_reference_id_type,
        }
        create_payment_method_request.update(
            {"payer_correlation_ids": payer_correlation_ids}
        )
    if request.set_default:
        create_payment_method_request.update({"set_default": str(request.set_default)})
    if request.is_scanned:
        create_payment_method_request.update({"is_scanned": str(request.is_scanned)})
    if request.create_payer_request:
        create_payer_request = {
            "payer_correlation_ids": {
                "payer_reference_id": request.create_payer_request.payer_reference_id,
                "payer_reference_id_type": request.create_payer_request.payer_reference_id_type,
            },
            "payer_reference_id": request.create_payer_request.payer_reference_id,
            "payer_reference_id_type": request.create_payer_request.payer_reference_id_type,
            "email": request.create_payer_request.email,
            "country": request.create_payer_request.country,
            "description": request.create_payer_request.description,
        }
        create_payment_method_request.update(
            {"create_payer_request": create_payer_request}
        )
    response = client.post(
        _create_payment_method_v1_url(), json=create_payment_method_request
    )
    assert response.status_code == http_status
    payment_method: dict = response.json()
    assert UUID(payment_method["id"], version=4)
    assert UUID(payment_method["payer_id"], version=4)
    if request.payer_id:
        assert payment_method["payer_id"] == request.payer_id
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
    assert payment_method["card"]["funding_type"] is not None
    # assert payment_method["dd_payer_id"] is not None
    return payment_method


def delete_payment_methods_v1(
    client: TestClient, payment_method_id: Any
) -> Dict[str, Any]:
    response = client.delete(
        _delete_payment_method_v1_url(payment_method_id=payment_method_id)
    )
    assert response.status_code == 200
    payment_method: dict = response.json()
    assert payment_method["deleted_at"] is not None
    return payment_method


def _list_payment_method_v0_url(
    dd_consumer_id, stripe_customer_id, country, active_only, sort_by, force_update
):
    base_request = f"{V0_PAYMENT_METHODS_ENDPOINT}?&active_only={active_only}&sort_by={sort_by}&country={country}"
    if dd_consumer_id:
        base_request = base_request + f"&dd_consumer_id={dd_consumer_id}"
    elif stripe_customer_id:
        base_request = base_request + f"&stripe_customer_id={stripe_customer_id}"
    if force_update:
        base_request = base_request + f"&force_update={force_update}"
    return base_request


def list_payment_method_v0(
    client: TestClient,
    dd_consumer_id: str = None,
    stripe_customer_id: str = None,
    country: CountryCode = CountryCode.US,
    active_only: bool = False,
    sort_by: PaymentMethodSortKey = PaymentMethodSortKey.CREATED_AT,
    force_update: bool = False,
) -> Dict[str, Any]:
    response = client.get(
        _list_payment_method_v0_url(
            dd_consumer_id=dd_consumer_id,
            stripe_customer_id=stripe_customer_id,
            country=country,
            active_only=active_only,
            sort_by=sort_by,
            force_update=force_update,
        )
    )
    assert response.status_code == 200
    payment_method_list: dict = response.json()
    return payment_method_list


def list_payment_method_v1(
    client: TestClient,
    active_only: bool = False,
    sort_by: PaymentMethodSortKey = PaymentMethodSortKey.CREATED_AT,
    force_update: bool = None,
    country: CountryCode = None,
    payer_id: Optional[str] = None,
    payer_reference_id: Optional[str] = None,
    payer_reference_id_type: Optional[str] = None,
) -> Dict[str, Any]:
    response = client.get(
        _list_payment_method_v1_url(
            payer_id=payer_id,
            payer_reference_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
            active_only=active_only,
            sort_by=sort_by,
            force_update=force_update,
            country=country,
        )
    )
    assert response.status_code == 200
    payment_method_list: dict = response.json()
    return payment_method_list


def list_payment_methods_v1_bad_request(
    client: TestClient,
    expected_http_code: int,
    expected_error_code: str,
    active_only: bool = False,
    sort_by: PaymentMethodSortKey = PaymentMethodSortKey.CREATED_AT,
    force_update: bool = None,
    country: CountryCode = None,
    payer_id: Optional[str] = None,
    payer_reference_id: Optional[str] = None,
    payer_reference_id_type: Optional[str] = None,
):
    response = client.get(
        _list_payment_method_v1_url(
            payer_id=payer_id,
            payer_reference_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
            active_only=active_only,
            sort_by=sort_by,
            force_update=force_update,
            country=country,
        )
    )
    assert response.status_code == expected_http_code
    pm_response: dict = response.json()
    assert pm_response["error_code"] == expected_error_code


def build_commando_processor(app_context: AppContext) -> CommandoProcessor:
    req_ctxt = build_req_context(app_context)
    payment_method_repo = PaymentMethodRepository(context=app_context)
    payer_repo = PayerRepository(context=app_context)
    cart_payment_repo = CartPaymentRepository(context=app_context)

    payment_method_client = PaymentMethodClient(
        payment_method_repo=payment_method_repo,
        log=req_ctxt.log,
        app_ctxt=app_context,
        stripe_async_client=req_ctxt.stripe_async_client,
    )

    payer_client = PayerClient(
        payer_repo=payer_repo,
        log=req_ctxt.log,
        app_ctxt=app_context,
        stripe_async_client=req_ctxt.stripe_async_client,
    )

    cart_payment_interface = CartPaymentInterface(
        app_context=app_context,
        req_context=req_ctxt,
        payment_repo=cart_payment_repo,
        payment_method_client=payment_method_client,
        payer_client=payer_client,
        stripe_async_client=req_ctxt.stripe_async_client,
    )

    legacy_payment_interface = LegacyPaymentInterface(
        app_context=app_context,
        req_context=req_ctxt,
        payment_repo=cart_payment_repo,
        stripe_async_client=req_ctxt.stripe_async_client,
    )

    return CommandoProcessor(
        log=req_ctxt.log,
        cart_payment_interface=cart_payment_interface,
        legacy_payment_interface=legacy_payment_interface,
        cart_payment_repo=cart_payment_repo,
    )
