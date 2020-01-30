import random
import uuid
from asyncio import AbstractEventLoop
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import pytest
import requests
from asynctest import mock
from starlette.testclient import TestClient

from app.commons.context.app_context import AppContext
from app.commons.operational_flags import (
    STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY,
    STRIPE_COMMANDO_MODE_BOOLEAN,
    VERIFY_CARD_IN_COMMANDO_MODE,
)
from app.commons.providers.stripe.stripe_models import Customer as StripeCustomer
from app.commons.types import CountryCode
from app.commons.utils.validation import not_none
from app.conftest import RuntimeContextManager, RuntimeSetter, StripeAPISettings
from app.payin.core.cart_payment.cart_payment_client import CartPaymentInterface
from app.payin.core.cart_payment.commando_mode_processor import CommandoProcessor

# Since this test requires a sequence of calls to stripe in order to set up a payment intent
# creation attempt, we need to use the actual test stripe system.  As a result this test class
# is marked as external.  The stripe simulator does not return the correct result since it does
# persist state.
from app.payin.core.cart_payment.types import LegacyStripeChargeStatus
from app.payin.core.payment_method.types import (
    CartPaymentSortKey,
    PaymentMethodSortKey,
    PgpPaymentInfo,
)
from app.payin.core.types import (
    PayerReferenceIdType,
    PgpPayerResourceId,
    PgpPaymentMethodResourceId,
)
from app.payin.models.maindb import stripe_charges
from app.payin.models.paymentdb import payment_methods, pgp_payment_methods
from app.payin.repository.payment_method_repo import (
    GetStripeCardByStripeIdInput,
    PaymentMethodRepository,
    StripeCardDbEntity,
)
from app.payin.test_integration.integration_utils import (
    _create_payer_v1_url,
    build_commando_processor,
    get_payer_by_id_v1,
    list_payment_method_v1,
)
from app.payin.tests import utils


@pytest.mark.external
class TestCartPayment:
    @pytest.fixture
    def payer(self, stripe_api: StripeAPISettings, client: TestClient):
        stripe_api.enable_outbound()
        return self._test_payer_creation(client=client)

    def _test_payer_creation(
        self, client: TestClient, payer_reference_id: str = "1"
    ) -> Dict[str, Any]:
        description_string = "SAMPLE_DESCRIPTION"
        create_payer_request = {
            "payer_correlation_ids": {
                "payer_reference_id": payer_reference_id,
                "payer_reference_id_type": "dd_drive_store_id",
            },
            "email": (description_string + "@dd.com"),
            "country": "US",
            "description": (description_string + "@dd.com"),
        }
        response = client.post(_create_payer_v1_url(), json=create_payer_request)
        assert response.status_code in (200, 201)
        payer: dict = response.json()
        return payer

    @pytest.fixture
    def payment_method(
        self, stripe_api: StripeAPISettings, client: TestClient, payer: Dict[str, Any]
    ):
        stripe_api.enable_outbound()
        return self._test_payment_method_creation(client, payer)

    def _get_payer_payment_method_request(
        self, payer: Dict[str, Any], token: str
    ) -> Dict[str, Any]:
        request_body = {
            "payer_id": payer["id"],
            "payment_gateway": "stripe",
            "token": token,
            "set_default": False,
            "is_scanned": False,
            "is_active": True,
        }
        return request_body

    def _test_payment_method_creation(
        self, client: TestClient, payer: Dict[str, Any], token: str = "tok_mastercard"
    ) -> Dict[str, Any]:
        request_body = self._get_payer_payment_method_request(payer, token)
        response = client.post("/payin/api/v1/payment_methods", json=request_body)
        assert response.status_code in (200, 201)
        payment_method = response.json()
        assert payment_method
        assert payment_method["id"]
        assert (
            payment_method["payment_gateway_provider_details"]["payment_provider"]
            == "stripe"
        )
        assert payment_method["dd_stripe_card_id"]
        assert payment_method["card"]
        assert payment_method["card"]["last4"]
        assert payment_method["card"]["exp_year"]
        assert payment_method["card"]["exp_month"]
        assert payment_method["card"]["fingerprint"]
        assert payment_method["card"]["active"]
        assert payment_method["card"]["country"]
        assert payment_method["card"]["brand"]
        assert payment_method["payment_gateway_provider_details"]["payment_method_id"]
        assert payment_method["payer_id"] == payer["id"]
        assert payment_method["type"] == "card"
        # assert payment_method["dd_payer_id"] is not None
        assert payer["created_at"]
        assert payer["updated_at"]
        assert payer["deleted_at"] is None
        return payment_method

    def _get_cart_payment_create_request(
        self,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        amount: int = 500,
        delay_capture: bool = True,
        split_payment: Dict[str, Any] = None,
        client_description: str = None,
        idempotency_key: Optional[str] = None,
        payer_id_extractor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        payment_method_extractor: Optional[
            Callable[[Dict[str, Any]], Dict[str, Any]]
        ] = None,
    ) -> Dict[str, Any]:

        if not payer_id_extractor:

            def payer_id_extractor_func(payer: Dict[str, Any]) -> Dict[str, Any]:
                return {"payer_id": payer["id"]}

            payer_id_extractor = payer_id_extractor_func

        if not payment_method_extractor:

            def payment_method_extractor_func(
                payment_method: Dict[str, Any]
            ) -> Dict[str, Any]:
                return {"payment_method_id": payment_method["id"]}

            payment_method_extractor = payment_method_extractor_func

        request_body = {
            "amount": amount,
            "payment_country": "US",
            "currency": "usd",
            "delay_capture": delay_capture,
            "client_description": f"{payer['id']} description"
            if not client_description
            else client_description,
            "payer_statement_description": f"{payer['id'][0:10]} statement",
            "correlation_ids": {"reference_id": "123", "reference_type": "3"},
        }

        payer_id_data = payer_id_extractor(payer)
        request_body.update(payer_id_data)

        payment_method_data = payment_method_extractor(payment_method)
        request_body.update(payment_method_data)

        if split_payment:
            request_body["split_payment"] = split_payment

        if not idempotency_key:
            request_body["idempotency_key"] = str(uuid.uuid4())

        return request_body

    def _get_cart_payment_create_legacy_payment_request(
        self,
        stripe_customer_id: str,
        stripe_card_id: str,
        merchant_country: CountryCode,
        amount: int = 500,
        idempotency_key: Optional[str] = None,
        split_payment: Optional[Dict[str, Any]] = None,
        dd_stripe_card_id: int = 1,
        client_description: str = None,
    ) -> Dict[str, Any]:
        # No payer_id or payment_method_id.  Instead we use legacy_payment.
        request_body = {
            "amount": amount,
            "currency": "usd",
            "delay_capture": True,
            "client_description": f"{stripe_customer_id} description"
            if not client_description
            else client_description,
            "payer_statement_description": f"{stripe_customer_id} bill"[-22:],
            "payer_country": "US",
            "payment_country": merchant_country.value,
            "split_payment": split_payment,
            "legacy_correlation_ids": {"reference_id": 123, "reference_type": 5},
            "legacy_payment": {
                "stripe_customer_id": stripe_customer_id,
                "stripe_card_id": stripe_card_id,
                "dd_country_id": 1,
                "dd_consumer_id": 1,
                "dd_additional_payment_info": {
                    "place_tag1": "place tag",
                    "extra info": "details",
                    "application_fee": 500,
                    "metadata": {"is_first_order": True},
                },
                "dd_stripe_card_id": f"{str(dd_stripe_card_id)}",
            },
        }

        if not idempotency_key:
            request_body["idempotency_key"] = str(uuid.uuid4())

        return request_body

    def _get_cart_payment_update_request(
        self,
        cart_payment: Dict[str, Any],
        amount: int,
        client_description: str,
        split_payment: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        request_body = {
            "amount": amount,
            "client_description": client_description,
            "legacy_payment": {
                "stripe_customer_id": "cus_9a8ds9",
                "stripe_card_id": "card_a819d",
                "dd_country_id": 1,
                "dd_consumer_id": 1,
                "dd_additional_payment_info": {
                    "place_tag2": "place tag two",
                    "extra items": "churro",
                },
                "dd_stripe_card_id": "987",
            },
        }

        if split_payment:
            request_body["split_payment"] = split_payment

        idempotency = idempotency_key if idempotency_key else str(uuid.uuid4())
        request_body["idempotency_key"] = idempotency
        return request_body

    def _get_legacy_cart_payment_update_request(
        self,
        cart_payment: Dict[str, Any],
        amount: int,
        client_description: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        request_body = {
            "amount": amount,
            "client_description": client_description,
            "dd_additional_payment_info": {
                "place_tag2": "place tag two",
                "application_fee": "90",
                "destination": "test_acct",
                "extra items": "churro",
            },
        }

        idempotency = idempotency_key if idempotency_key else str(uuid.uuid4())
        request_body["idempotency_key"] = idempotency
        return request_body

    def _get_random_charge_id(self, charge_id):
        while True:
            id = random.randint(1, 100000)
            if id != charge_id:
                return id

    def _create_cart_payment_legacy_get_raw_response(
        self,
        client: TestClient,
        stripe_customer_id: str,
        stripe_card_id: str,
        amount: int,
        merchant_country: CountryCode,
        split_payment: Optional[Dict[str, Any]] = None,
        dd_stripe_card_id: int = 1,
        client_description: Optional[str] = None,
    ) -> requests.Response:

        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer_id,
            stripe_card_id=stripe_card_id,
            amount=amount,
            split_payment=split_payment,
            merchant_country=merchant_country,
            dd_stripe_card_id=dd_stripe_card_id,
            client_description=client_description,
        )

        return client.post("/payin/api/v0/cart_payments", json=request_body)

    def _get_cart_payment_get_legacy_response(
        self, client: TestClient, dd_charge_id: str
    ) -> requests.Response:
        return client.get(
            f"/payin/api/v0/cart_payments/get_by_charge_id?dd_charge_id={dd_charge_id}"
        )

    def _get_cart_payment_get_response(
        self, client: TestClient, cart_payment_id: str
    ) -> requests.Response:
        return client.get(f"/payin/api/v1/cart_payments/{cart_payment_id}")

    def _test_cart_payment_legacy_payment_creation(
        self,
        client: TestClient,
        stripe_customer_id: str,
        stripe_card_id: str,
        amount: int,
        merchant_country: CountryCode,
        split_payment: Optional[Dict[str, Any]] = None,
        client_description: str = None,
        dd_stripe_card_id: int = 1,
        commando_mode: bool = False,
    ) -> Dict[str, Any]:
        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer_id,
            stripe_card_id=stripe_card_id,
            amount=amount,
            split_payment=split_payment,
            merchant_country=merchant_country,
            dd_stripe_card_id=dd_stripe_card_id,
            client_description=client_description,
        )

        response = self._create_cart_payment_legacy_get_raw_response(
            client=client,
            stripe_customer_id=stripe_customer_id,
            stripe_card_id=stripe_card_id,
            amount=amount,
            split_payment=split_payment,
            merchant_country=merchant_country,
            dd_stripe_card_id=dd_stripe_card_id,
            client_description=client_description,
        )
        assert response.status_code == 201
        cart_payment = response.json()

        # For legacy based payments, payer_id and payment_method_id keys are expected in the body
        # but value is None.  Legacy payment must be defined and match request.
        assert cart_payment
        assert cart_payment["id"]
        assert cart_payment["amount"] == request_body["amount"]
        assert cart_payment["payer_id"] is None
        assert cart_payment["payment_method_id"] is None
        assert cart_payment["delay_capture"] == request_body["delay_capture"]
        assert cart_payment["correlation_ids"]
        assert cart_payment["correlation_ids"]["reference_id"] == str(
            request_body["legacy_correlation_ids"]["reference_id"]
        )
        assert cart_payment["correlation_ids"]["reference_type"] == str(
            request_body["legacy_correlation_ids"]["reference_type"]
        )
        assert cart_payment["client_description"] == request_body["client_description"]
        statement_description = cart_payment["payer_statement_description"]
        assert statement_description == request_body["payer_statement_description"]
        expected_split_payment = (
            request_body["split_payment"] if "split_payment" in request_body else None
        )
        assert cart_payment["split_payment"] == expected_split_payment
        assert cart_payment["created_at"]
        assert cart_payment["updated_at"]
        assert cart_payment["deleted_at"] is None
        assert cart_payment["dd_charge_id"]
        assert type(cart_payment["dd_charge_id"]) is int
        assert cart_payment["deferred"] == commando_mode
        return cart_payment

    def _test_cart_payment_legacy_payment_get(
        self, client: TestClient, dd_charge_id: str
    ) -> Dict[str, Any]:
        response = self._get_cart_payment_get_legacy_response(
            client=client, dd_charge_id=dd_charge_id
        )
        assert response.status_code == 200
        cart_payment = response.json()
        assert cart_payment
        assert cart_payment["dd_charge_id"] == dd_charge_id
        return cart_payment

    def _test_cart_payment_get(
        self, client: TestClient, cart_payment_id: str
    ) -> Dict[str, Any]:
        response = self._get_cart_payment_get_response(
            client=client, cart_payment_id=cart_payment_id
        )
        assert response.status_code == 200
        cart_payment = response.json()
        assert cart_payment
        assert cart_payment["id"] == cart_payment_id
        return cart_payment

    def _test_cart_payment_get_not_found(
        self, client: TestClient, cart_payment_id: str
    ):
        response = self._get_cart_payment_get_response(
            client=client, cart_payment_id=cart_payment_id
        )
        assert response.status_code == 404

    def _test_cart_payment_creation(
        self,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        amount: int,
        delay_capture: bool,
        split_payment: Optional[Dict[str, Any]] = None,
        client_description: str = None,
        commando_mode: bool = False,
        payer_id_extractor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        payment_method_extractor: Optional[
            Callable[[Dict[str, Any]], Dict[str, Any]]
        ] = None,
    ) -> Dict[str, Any]:
        request_body = self._get_cart_payment_create_request(
            payer,
            payment_method,
            amount,
            delay_capture,
            split_payment,
            client_description=client_description,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )
        response = client.post("/payin/api/v1/cart_payments", json=request_body)
        assert response.status_code in (200, 201)
        cart_payment = response.json()
        assert cart_payment
        assert cart_payment["id"]
        assert cart_payment["amount"] == request_body["amount"]
        assert cart_payment["payer_id"] == payer["id"]
        if "payment_method_token" in request_body:
            assert cart_payment["payment_method_id"]
        if "payment_method_id" in request_body:
            assert (
                cart_payment["payment_method_id"] == request_body["payment_method_id"]
            )
        if "dd_stripe_card_id" in request_body:
            assert (
                cart_payment["dd_stripe_card_id"] == request_body["dd_stripe_card_id"]
            )
        assert cart_payment["delay_capture"] == request_body["delay_capture"]
        assert cart_payment["correlation_ids"]
        assert (
            cart_payment["correlation_ids"]["reference_id"]
            == request_body["correlation_ids"]["reference_id"]
        )
        assert (
            cart_payment["correlation_ids"]["reference_type"]
            == request_body["correlation_ids"]["reference_type"]
        )
        assert cart_payment["metadata"] is None
        assert cart_payment["client_description"] == request_body["client_description"]
        statement_description = cart_payment["payer_statement_description"]
        assert statement_description == request_body["payer_statement_description"]
        split_payment = (
            request_body["split_payment"] if "split_payment" in request_body else None
        )
        assert cart_payment["split_payment"] == split_payment
        assert cart_payment["created_at"]
        assert cart_payment["updated_at"]
        assert cart_payment["deleted_at"] is None
        assert cart_payment["deferred"] == commando_mode

        if payer_id_extractor:
            expected_payer_ids = payer_id_extractor(payer)
            for payer_id_key, payer_id_val in expected_payer_ids.items():
                assert payer_id_key in cart_payment
                assert payer_id_val == cart_payment[payer_id_key]

        return cart_payment

    def _test_cart_payment_error(
        self,
        client: TestClient,
        resource_path: str,
        request_body: Dict[str, Any],
        expected_http_status_status_code: int,
        expected_body_error_code: str,
        expected_retryable: bool,
    ) -> None:
        response = client.post(resource_path, json=request_body)
        body = response.json()
        assert response.status_code == expected_http_status_status_code
        assert "error_code" in body
        assert body["error_code"] == expected_body_error_code
        assert "error_message" in body
        assert "retryable" in body
        assert body["retryable"] == expected_retryable

    def _test_cart_payment_legacy_cancel(
        self, client: TestClient, charge_id: int
    ) -> None:
        response = client.post(
            f"/payin/api/v0/cart_payments/{str(charge_id)}/cancel", json={}
        )
        assert response.status_code == 200
        cart_payment = response.json()
        assert cart_payment["id"]

        # Idempotent delete
        response = client.post(
            f"/payin/api/v0/cart_payments/{str(charge_id)}/cancel", json={}
        )
        assert response.status_code == 200
        cart_payment = response.json()
        assert cart_payment["id"]
        assert cart_payment["deleted_at"] is not None
        assert cart_payment["updated_at"] == cart_payment["deleted_at"]

    def _test_cancel_cart_payment(
        self, client: TestClient, cart_payment: Dict[str, Any]
    ) -> None:
        response = client.post(
            f"/payin/api/v1/cart_payments/{str(cart_payment['id'])}/cancel", json={}
        )
        assert response.status_code == 200
        cart_payment = response.json()
        assert cart_payment["id"]

        # Idempotent delete
        response = client.post(
            f"/payin/api/v1/cart_payments/{str(cart_payment['id'])}/cancel", json={}
        )
        assert response.status_code == 200
        cart_payment = response.json()
        assert cart_payment["id"]
        assert cart_payment["deleted_at"] is not None
        assert cart_payment["deleted_at"] == cart_payment["updated_at"]

    def _test_cancel_cart_payment_error(
        self,
        client: TestClient,
        cart_payment_id: uuid.UUID,
        expected_http_status_status_code: int,
        expected_body_error_code: str,
        expected_retryable: bool,
    ) -> None:
        self._test_cart_payment_error(
            client,
            f"/payin/api/v1/cart_payments/{str(cart_payment_id)}/cancel",
            {},
            expected_http_status_status_code,
            expected_body_error_code,
            expected_retryable,
        )

    def _test_legacy_cart_payment_adjustment(
        self,
        client: TestClient,
        cart_payment: Dict[str, Any],
        charge_id: int,
        amount: int,
        original_amount: int,
    ) -> None:
        request_body = self._get_legacy_cart_payment_update_request(
            cart_payment=cart_payment,
            amount=amount,
            client_description=f"{cart_payment['client_description']}-updated",
        )
        response = client.post(
            f"/payin/api/v0/cart_payments/{str(charge_id)}/adjust", json=request_body
        )
        body = response.json()
        assert response.status_code == 200
        assert body["id"] == cart_payment["id"]
        assert body["amount"] == original_amount + int(request_body["amount"])
        assert body["payer_id"] == cart_payment["payer_id"]
        assert body["payment_method_id"] == cart_payment["payment_method_id"]
        assert body["delay_capture"] == cart_payment["delay_capture"]
        assert body["correlation_ids"] == cart_payment["correlation_ids"]
        assert body["client_description"] == request_body["client_description"]
        statement_description = body["payer_statement_description"]
        assert statement_description == cart_payment["payer_statement_description"]
        assert body["deferred"] == False

    def _test_legacy_update_cart_payment_not_found_error(
        self,
        client: TestClient,
        cart_payment: Dict[str, Any],
        charge_id: int,
        amount: int,
        original_amount: int,
        payin_error_code: str = "payin_61",
    ) -> None:
        request_body = self._get_legacy_cart_payment_update_request(
            cart_payment=cart_payment,
            amount=amount,
            client_description=f"{cart_payment['client_description']}-updated",
        )
        self._test_cart_payment_error(
            client,
            f"/payin/api/v0/cart_payments/{str(charge_id)}/adjust",
            request_body,
            404,
            payin_error_code,
            False,
        )

    def _test_adjust_cart_payment_not_found_error(
        self,
        client: TestClient,
        cart_payment: Dict[str, Any],
        request_body: Dict[str, Any],
        expected_http_status_status_code: int,
        expected_body_error_code: str,
        expected_retryable: bool,
    ) -> None:
        self._test_cart_payment_error(
            client,
            f"/payin/api/v1/cart_payments/{str(uuid.uuid4())}/adjust",
            request_body,
            expected_http_status_status_code,
            expected_body_error_code,
            expected_retryable,
        )

    def _test_legacy_cart_payment_creation_error(
        self,
        client: TestClient,
        request_body: Dict[str, Any],
        expected_http_status_status_code: int,
        expected_body_error_code: str,
        expected_retryable: bool,
    ) -> None:
        self._test_cart_payment_error(
            client,
            "/payin/api/v0/cart_payments",
            request_body,
            expected_http_status_status_code,
            expected_body_error_code,
            expected_retryable,
        )

    def _test_cart_payment_creation_error(
        self,
        client: TestClient,
        request_body: Dict[str, Any],
        expected_http_status_status_code: int,
        expected_body_error_code: str,
        expected_retryable: bool,
    ) -> None:
        self._test_cart_payment_error(
            client,
            "/payin/api/v1/cart_payments",
            request_body,
            expected_http_status_status_code,
            expected_body_error_code,
            expected_retryable,
        )

    def _test_cart_payment_update_error(
        self,
        client: TestClient,
        cart_payment: Dict[str, Any],
        request_body: Dict[str, Any],
        expected_http_status_status_code: int,
        expected_body_error_code: str,
        expected_retryable: bool,
    ) -> None:
        self._test_cart_payment_error(
            client,
            f"/payin/api/v1/cart_payments/{str(cart_payment['id'])}/adjust",
            request_body,
            expected_http_status_status_code,
            expected_body_error_code,
            expected_retryable,
        )

    def _test_cart_payment_adjustment(
        self,
        client: TestClient,
        cart_payment: Dict[str, Any],
        amount: int,
        split_payment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_body = self._get_cart_payment_update_request(
            cart_payment=cart_payment,
            amount=amount,
            client_description=f"{cart_payment['client_description']}-updated",
            split_payment=split_payment,
        )
        response = client.post(
            f"/payin/api/v1/cart_payments/{str(cart_payment['id'])}/adjust",
            json=request_body,
        )
        body = response.json()
        assert response.status_code == 200
        assert body["id"] == cart_payment["id"]
        assert body["amount"] == request_body["amount"]
        assert body["payer_id"] == cart_payment["payer_id"]
        assert body["payment_method_id"] == cart_payment["payment_method_id"]
        assert body["delay_capture"] == cart_payment["delay_capture"]
        assert body["correlation_ids"] == cart_payment["correlation_ids"]
        assert body["client_description"] == request_body["client_description"]
        statement_description = body["payer_statement_description"]
        assert statement_description == cart_payment["payer_statement_description"]
        expected_split_payment = (
            split_payment if split_payment else cart_payment["split_payment"]
        )
        assert body["split_payment"] == expected_split_payment
        assert body["deferred"] == False
        return body

    def _list_cart_payment_get_legacy_response(
        self,
        client: TestClient,
        dd_consumer_id: str,
        created_at_gte: Optional[datetime],
        created_at_lte: Optional[datetime],
        sort_by: CartPaymentSortKey,
    ) -> requests.Response:
        base_request = f"/payin/api/v0/cart_payments?dd_consumer_id={dd_consumer_id}&sort_by={sort_by}"
        if created_at_gte:
            base_request = base_request + f"&created_at_gte={created_at_gte}"
        if created_at_lte:
            base_request = base_request + f"&created_at_lte={created_at_lte}"
        return client.get(base_request)

    def _list_cart_payment_response(
        self,
        client: TestClient,
        created_at_gte: Optional[datetime],
        created_at_lte: Optional[datetime],
        sort_by: CartPaymentSortKey,
        payer_id: Optional[str] = None,
        payer_reference_id: Optional[str] = None,
        payer_reference_id_type: Optional[str] = None,
    ) -> requests.Response:
        base_request = f"/payin/api/v1/cart_payments?sort_by={sort_by}"
        if created_at_gte:
            base_request = base_request + f"&created_at_gte={created_at_gte}"
        if created_at_lte:
            base_request = base_request + f"&created_at_lte={created_at_lte}"
        if payer_id:
            base_request = base_request + f"&payer_id={payer_id}"
        else:
            base_request = (
                base_request
                + f"&payer_reference_id={payer_reference_id}&payer_reference_id_type={payer_reference_id_type}"
            )
        return client.get(base_request)

    def test_cancellation(
        self, client: TestClient, payer: Dict[str, Any], payment_method: Dict[str, Any]
    ):
        # Uncaptured payment
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=500,
            delay_capture=True,
        )
        # Cancel previous cart payment - pending payment intent in provider will be cancelled.
        self._test_cancel_cart_payment(client=client, cart_payment=cart_payment)

        # Cancel a cart payment which is not present. 404 expected
        self._test_cancel_cart_payment_error(
            client=client,
            cart_payment_id=uuid.uuid4(),
            expected_http_status_status_code=404,
            expected_body_error_code="payin_61",
            expected_retryable=False,
        )

        # Auto captured payment
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=600,
            delay_capture=False,
        )
        # Cancel previous cart payment, resulting in provider refund of already captured intent
        self._test_cancel_cart_payment(client=client, cart_payment=cart_payment)

    def test_cancellation_after_adjustments(
        self, stripe_api: StripeAPISettings, client: TestClient
    ):
        stripe_api.enable_outbound()
        payer = self._test_payer_creation(client)
        payment_method = self._test_payment_method_creation(client, payer)

        # Initial payment, delay capture
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=525,
            delay_capture=True,
        )

        # Adjust up once
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=650
        )

        # Adjust up again
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=770
        )

        # Bring down once
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=680
        )

        # Reduce again
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=480
        )

        # Now cancel
        self._test_cancel_cart_payment(client=client, cart_payment=cart_payment)
        self._test_cancel_cart_payment(client=client, cart_payment=cart_payment)

    def test_cart_payment_multiple_adjustments_up_then_down(
        self, stripe_api: StripeAPISettings, client: TestClient
    ):
        stripe_api.enable_outbound()
        payer = self._test_payer_creation(client)
        payment_method = self._test_payment_method_creation(client, payer)

        # Initial payment, delay capture
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=525,
            delay_capture=True,
        )

        # Adjust up once
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=650
        )

        # Adjust up again
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=770
        )

        # Bring down once
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=680
        )

        # Reduce again
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=480
        )

    def test_cart_payment_multiple_adjustments_down_then_up(
        self, stripe_api: StripeAPISettings, client: TestClient
    ):
        stripe_api.enable_outbound()
        payer = self._test_payer_creation(client)
        payment_method = self._test_payment_method_creation(client, payer)

        # Initial payment, delay capture
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=560,
            delay_capture=True,
        )

        # Bring down once
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=540
        )

        # Reduce again
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=430
        )

        # Adjust up once
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=535
        )

        # Adjust up again
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=870
        )

    def test_cart_payment_adjustment_after_capture(
        self, stripe_api: StripeAPISettings, client: TestClient
    ):
        stripe_api.enable_outbound()
        payer = self._test_payer_creation(client)
        payment_method = self._test_payment_method_creation(client, payer)

        # Initial payment, immediate capture
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=440,
            delay_capture=False,
        )

        # Bring down once
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=400
        )

        # Bring down again
        self._test_cart_payment_adjustment(
            client=client, cart_payment=cart_payment, amount=300
        )

    def test_cart_payment_multiple_adjustments_mixed_up_and_down(
        self, stripe_api: StripeAPISettings, client: TestClient
    ):
        stripe_api.enable_outbound()
        payer = self._test_payer_creation(client)
        payment_method = self._test_payment_method_creation(client, payer)

        # Initial payment, delay capture
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=440,
            delay_capture=True,
        )

        # Adjust up once
        updated_cart_payment = self._test_cart_payment_adjustment(
            client=client,
            cart_payment=cart_payment,
            amount=690,
            split_payment={
                "application_fee_amount": 80,
                "payout_account_id": "acct_1FKYqjDpmxeDAkcx",
            },
        )

        # Bring down once
        updated_cart_payment = self._test_cart_payment_adjustment(
            client=client, cart_payment=updated_cart_payment, amount=510
        )

        # Adjust up again
        updated_cart_payment = self._test_cart_payment_adjustment(
            client=client,
            cart_payment=updated_cart_payment,
            amount=610,
            split_payment={
                "application_fee_amount": 70,
                "payout_account_id": "acct_1FKYqjDpmxeDAkcx",
            },
        )

        # Adjust down again, this time down to zero
        updated_cart_payment = self._test_cart_payment_adjustment(
            client=client, cart_payment=updated_cart_payment, amount=0
        )

    def test_cart_payment_adjustment_with_split_payment(
        self, stripe_api: StripeAPISettings, client: TestClient
    ):
        stripe_api.enable_outbound()
        payer = self._test_payer_creation(client)
        payment_method = self._test_payment_method_creation(client, payer)

        # Initial payment, delay capture set to False for immediate capture.  This option is used to
        # verify refund handling where split_payment is involved
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=340,
            delay_capture=False,
            split_payment={
                "application_fee_amount": 60,
                "payout_account_id": "acct_1FKYqjDpmxeDAkcx",
            },
        )

        # Adjust up once
        updated_cart_payment = self._test_cart_payment_adjustment(
            client=client,
            cart_payment=cart_payment,
            amount=790,
            split_payment={
                "application_fee_amount": 120,
                "payout_account_id": "acct_1FKYqjDpmxeDAkcx",
            },
        )

        # Bring down once
        updated_cart_payment = self._test_cart_payment_adjustment(
            client=client, cart_payment=updated_cart_payment, amount=410
        )

    @pytest.mark.parametrize("commando_mode", [True, False])
    def test_cart_payment_creation_with_payer_id_payment_method_id(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        runtime_setter: RuntimeSetter,
        commando_mode: bool,
        app_context: AppContext,
        event_loop: AbstractEventLoop,
    ):
        def payer_id_extractor(payer: Dict[str, Any]) -> Dict[str, Any]:
            return {"payer_id": payer["id"]}

        def payment_method_extractor(payment_method: Dict[str, Any]) -> Dict[str, Any]:
            return {"payment_method_id": payment_method["id"]}

        self._test_cart_payment_creation_flows(
            stripe_api=stripe_api,
            client=client,
            payer=payer,
            payment_method=payment_method,
            runtime_setter=runtime_setter,
            commando_mode=commando_mode,
            app_context=app_context,
            event_loop=event_loop,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )

    @pytest.mark.parametrize("commando_mode", [True, False])
    def test_cart_payment_creation_with_dd_stripe_customer_id_payment_method_id(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        runtime_setter: RuntimeSetter,
        commando_mode: bool,
        app_context: AppContext,
        event_loop: AbstractEventLoop,
    ):
        def payer_id_extractor(payer: Dict[str, Any]) -> Dict[str, Any]:
            legacy_dd_stripe_customer_id = payer["legacy_dd_stripe_customer_id"]
            payer_correlation_ids = {
                "payer_reference_id": legacy_dd_stripe_customer_id,
                "payer_reference_id_type": PayerReferenceIdType.LEGACY_DD_STRIPE_CUSTOMER_ID.value,
            }
            return {"payer_correlation_ids": payer_correlation_ids}

        def payment_method_extractor(payment_method: Dict[str, Any]) -> Dict[str, Any]:
            return {"payment_method_id": payment_method["id"]}

        self._test_cart_payment_creation_flows(
            stripe_api=stripe_api,
            client=client,
            payer=payer,
            payment_method=payment_method,
            runtime_setter=runtime_setter,
            commando_mode=commando_mode,
            app_context=app_context,
            event_loop=event_loop,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )

    @pytest.mark.parametrize("commando_mode", [True, False])
    def test_cart_payment_creation_with_payer_id_dd_stripe_card_id(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        runtime_setter: RuntimeSetter,
        commando_mode: bool,
        app_context: AppContext,
        event_loop: AbstractEventLoop,
    ):
        def payer_id_extractor(payer: Dict[str, Any]) -> Dict[str, Any]:
            return {"payer_id": payer["id"]}

        def payment_method_extractor(payment_method: Dict[str, Any]) -> Dict[str, Any]:
            return {"dd_stripe_card_id": payment_method["dd_stripe_card_id"]}

        self._test_cart_payment_creation_flows(
            stripe_api=stripe_api,
            client=client,
            payer=payer,
            payment_method=payment_method,
            runtime_setter=runtime_setter,
            commando_mode=commando_mode,
            app_context=app_context,
            event_loop=event_loop,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )

    @pytest.mark.parametrize("commando_mode", [True, False])
    def test_cart_payment_creation_with_payer_id_dd_stripe_card_id_without_pgp_payment_method(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        runtime_setter: RuntimeSetter,
        commando_mode: bool,
        app_context: AppContext,
        event_loop: AbstractEventLoop,
    ):
        def payer_id_extractor(payer: Dict[str, Any]) -> Dict[str, Any]:
            return {"payer_id": payer["id"]}

        def payment_method_extractor(payment_method: Dict[str, Any]) -> Dict[str, Any]:
            return {"dd_stripe_card_id": payment_method["dd_stripe_card_id"]}

        # ugly hack to setup well formed pm, ppm and sc then remove pm and ppm from data store to simulate
        # payer with sc without pm.
        request_body = self._get_payer_payment_method_request(payer, "tok_visa")
        response = client.post("/payin/api/v1/payment_methods", json=request_body)
        assert response.status_code in (200, 201)
        payment_method = response.json()
        assert payment_method

        event_loop.run_until_complete(
            app_context.payin_paymentdb.master().execute(
                payment_methods.table.delete().where(
                    payment_methods.id == payment_method["id"]
                )
            )
        )

        event_loop.run_until_complete(
            app_context.payin_paymentdb.master().execute(
                pgp_payment_methods.table.delete().where(
                    pgp_payment_methods.payment_method_id == payment_method["id"]
                )
            )
        )

        assert not event_loop.run_until_complete(
            app_context.payin_paymentdb.master().execute(
                pgp_payment_methods.table.select().where(
                    pgp_payment_methods.payment_method_id == payment_method["id"]
                )
            )
        )

        assert not event_loop.run_until_complete(
            app_context.payin_paymentdb.master().execute(
                payment_methods.table.select().where(
                    payment_methods.id == payment_method["id"]
                )
            )
        )

        self._test_cart_payment_creation_flows(
            stripe_api=stripe_api,
            client=client,
            payer=payer,
            payment_method=payment_method,
            runtime_setter=runtime_setter,
            commando_mode=commando_mode,
            app_context=app_context,
            event_loop=event_loop,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )

    @pytest.mark.parametrize("commando_mode", [True, False])
    def test_cart_payment_creation_with_dd_stripe_customer_id_dd_stripe_card_id(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        runtime_setter: RuntimeSetter,
        commando_mode: bool,
        app_context: AppContext,
        event_loop: AbstractEventLoop,
    ):
        def payer_id_extractor(payer: Dict[str, Any]) -> Dict[str, Any]:
            legacy_dd_stripe_customer_id = payer["legacy_dd_stripe_customer_id"]
            payer_correlation_ids = {
                "payer_reference_id": legacy_dd_stripe_customer_id,
                "payer_reference_id_type": PayerReferenceIdType.LEGACY_DD_STRIPE_CUSTOMER_ID,
            }
            return {"payer_correlation_ids": payer_correlation_ids}

        def payment_method_extractor(payment_method: Dict[str, Any]) -> Dict[str, Any]:
            return {"dd_stripe_card_id": payment_method["dd_stripe_card_id"]}

        self._test_cart_payment_creation_flows(
            stripe_api=stripe_api,
            client=client,
            payer=payer,
            payment_method=payment_method,
            runtime_setter=runtime_setter,
            commando_mode=commando_mode,
            app_context=app_context,
            event_loop=event_loop,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )

    @pytest.mark.parametrize("commando_mode", [True, False])
    def test_cart_payment_creation_with_stripe_token_for_new_payer(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        runtime_setter: RuntimeSetter,
        commando_mode: bool,
        payer: Dict[str, Any],
        app_context: AppContext,
    ):
        def payer_id_extractor(payer: Dict[str, Any]) -> Dict[str, Any]:
            legacy_dd_stripe_customer_id = payer["legacy_dd_stripe_customer_id"]
            payer_correlation_ids = {
                "payer_reference_id": legacy_dd_stripe_customer_id,
                "payer_reference_id_type": PayerReferenceIdType.LEGACY_DD_STRIPE_CUSTOMER_ID,
            }
            return {"payer_correlation_ids": payer_correlation_ids}

        def payment_method_extractor(payment_method: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "payment_method_token": {
                    "token": "tok_amex",
                    "payment_gateway": "stripe",
                }
            }

        runtime_setter.set(STRIPE_COMMANDO_MODE_BOOLEAN, commando_mode)

        # verify the payer is a new one and there is no existing payment method associated
        existing_pms = list_payment_method_v1(
            client=client,
            payer_id=payer["id"],
            active_only=True,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
            country=CountryCode.US,
        )

        cp_1 = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method={},
            amount=500,
            delay_capture=True,
            commando_mode=commando_mode,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )
        new_pm_id = cp_1.get("payment_method_id", None)
        assert new_pm_id

        # Use same token for a second create cp call to test pm deduplication
        cp_2 = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method={},
            amount=500,
            delay_capture=True,
            commando_mode=commando_mode,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )
        assert new_pm_id == cp_2["payment_method_id"]

        current_pms = list_payment_method_v1(
            client=client,
            payer_id=payer["id"],
            active_only=True,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
            country=CountryCode.US,
        )

        assert "count" in current_pms
        # there should only be at most 1 pm created given dedupe
        assert 0 <= (current_pms["count"] - existing_pms["count"]) <= 1
        current_pm = current_pms["data"][0]
        assert not current_pm.get("deleted_at", None)
        assert current_pm.get("card", None)
        assert current_pm.get("card").get("active", False)

        current_payer = get_payer_by_id_v1(client, payer["id"])
        assert current_payer["id"] == payer["id"]
        # there shouldn't be default pm attached here since we don't set default pm for token payment
        assert not current_payer["default_payment_method_id"]

    def _test_cart_payment_creation_flows(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        runtime_setter: RuntimeSetter,
        commando_mode: bool,
        app_context: AppContext,
        event_loop: AbstractEventLoop,
        payer_id_extractor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        payment_method_extractor: Optional[
            Callable[[Dict[str, Any]], Dict[str, Any]]
        ] = None,
    ):
        stripe_api.enable_outbound()
        runtime_setter.set(STRIPE_COMMANDO_MODE_BOOLEAN, commando_mode)

        # Recoup all existing pending cp to have a clean start
        if commando_mode:
            with RuntimeContextManager(
                STRIPE_COMMANDO_MODE_BOOLEAN, False, runtime_setter
            ):
                commando_processor: CommandoProcessor = build_commando_processor(
                    app_context=app_context
                )
                event_loop.run_until_complete(commando_processor.recoup())

        amounts = (500, 600, 560)

        # Success case: intent created, not captured yet
        self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=500,
            delay_capture=True,
            commando_mode=commando_mode,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )

        # Success case: intent created, auto captured
        self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=600,
            delay_capture=False,
            commando_mode=commando_mode,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )

        # Split payment use
        split_payment = {
            "payout_account_id": "acct_1FKYqjDpmxeDAkcx",  # Pre-seeded stripe sandbox testing account
            "application_fee_amount": 20,
        }
        self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=560,
            delay_capture=False,
            split_payment=split_payment,
            commando_mode=commando_mode,
            payer_id_extractor=payer_id_extractor,
            payment_method_extractor=payment_method_extractor,
        )

        # Other payer cannot use some else's payment method for cart payment creation
        with RuntimeContextManager(STRIPE_COMMANDO_MODE_BOOLEAN, False, runtime_setter):
            other_payer = self._test_payer_creation(
                client, payer_reference_id=str(random.randint(2, 1000))
            )

            # Why do we need to patch here? see: https://doordash.atlassian.net/browse/PAYIN-340
            with mock.patch.object(
                CartPaymentInterface,
                "get_pgp_payment_info_v1",
                return_value=(
                    PgpPaymentInfo(
                        pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                            payment_method["payment_gateway_provider_details"][
                                "payment_method_id"
                            ]
                        ),
                        pgp_payer_resource_id=PgpPayerResourceId(
                            other_payer["payment_gateway_provider_customers"][0][
                                "payment_provider_customer_id"
                            ]
                        ),
                    ),
                    utils.generate_legacy_payment(),
                ),
            ):

                request_body = self._get_cart_payment_create_request(
                    payer=payer,
                    payment_method=payment_method,
                    payer_id_extractor=payer_id_extractor,
                    payment_method_extractor=payment_method_extractor,
                )
                self._test_cart_payment_creation_error(
                    client, request_body, 403, "payin_52", False
                )

        if commando_mode:
            with RuntimeContextManager(
                STRIPE_COMMANDO_MODE_BOOLEAN, False, runtime_setter
            ):
                commando_processor = build_commando_processor(app_context=app_context)
                total, result = event_loop.run_until_complete(
                    commando_processor.recoup()
                )

                for r in result:
                    assert r[1] in amounts

                assert total == 3

    def test_cart_payment_creation_cross_country(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        app_context: AppContext,
    ):
        stripe_api.enable_outbound()

        request_body = self._get_cart_payment_create_request(
            payer, payment_method, amount=500, delay_capture=False, split_payment=None
        )
        request_body["payment_country"] = "AU"
        response = client.post("/payin/api/v1/cart_payments", json=request_body)
        assert response.status_code == 201

    def test_cart_payment_creation_invalid_amount(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        app_context: AppContext,
    ):
        stripe_api.enable_outbound()
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, amount=30, delay_capture=False, split_payment=None
        )
        request_body["payment_country"] = "US"
        response = client.post("/payin/api/v1/cart_payments", json=request_body)
        assert response is not None
        assert response.status_code == 400
        assert response.reason == "Bad Request"

    def test_cart_payment_creation_cross_country_legacy(
        self,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        app_context: AppContext,
    ):
        provider_account_id = payer["payment_gateway_provider_customers"][0][
            "payment_provider_customer_id"
        ]

        provider_card_id = payment_method["payment_gateway_provider_details"][
            "payment_method_id"
        ]
        cart_payment = self._test_cart_payment_legacy_payment_creation(
            client=client,
            stripe_customer_id=provider_account_id,
            stripe_card_id=provider_card_id,
            amount=900,
            merchant_country=CountryCode.AU,
        )
        assert cart_payment

    def test_cart_payment_creation_with_commando_white_list(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        runtime_setter: RuntimeSetter,
        app_context: AppContext,
        event_loop: AbstractEventLoop,
    ):
        stripe_api.enable_outbound()
        payer = self._test_payer_creation(client=client, payer_reference_id="1")
        payment_method = self._test_payment_method_creation(client=client, payer=payer)
        runtime_setter.set(STRIPE_COMMANDO_MODE_BOOLEAN, False)
        # Use payer, payment method api calls to seed data into legacy table.  It would be better to
        # create directly in legacy system without creating corresponding records in the new tables since
        # that is a more realistic case, but there is not yet an easy way to set this up.
        provider_account_id = payer["payment_gateway_provider_customers"][0][
            "payment_provider_customer_id"
        ]

        provider_card_id = payment_method["payment_gateway_provider_details"][
            "payment_method_id"
        ]

        payment_method_repository = PaymentMethodRepository(app_context)

        stripe_card: StripeCardDbEntity = not_none(
            event_loop.run_until_complete(
                payment_method_repository.get_stripe_card_by_stripe_id(
                    input=GetStripeCardByStripeIdInput(stripe_id=provider_card_id)
                )
            )
        )

        assert stripe_card.id

        commando_processor: CommandoProcessor = build_commando_processor(
            app_context=app_context
        )

        event_loop.run_until_complete(commando_processor.recoup())

        cart_payment_1 = self._test_cart_payment_legacy_payment_creation(
            client=client,
            stripe_customer_id=provider_account_id,
            stripe_card_id=provider_card_id,
            amount=900,
            merchant_country=CountryCode.US,
            dd_stripe_card_id=stripe_card.id,
        )

        assert cart_payment_1

        # Client provides Stripe customer ID and Stripe customer ID, instead of payer_id and payment_method_id
        # With allow all payment intent in commando mode
        with RuntimeContextManager(
            STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY, [1], runtime_setter
        ), RuntimeContextManager(VERIFY_CARD_IN_COMMANDO_MODE, False, runtime_setter):
            cart_payment_2 = self._test_cart_payment_legacy_payment_creation(
                client=client,
                stripe_customer_id=provider_account_id,
                stripe_card_id=provider_card_id,
                amount=700,
                merchant_country=CountryCode.US,
                dd_stripe_card_id=stripe_card.id,
                commando_mode=True,
            )
            assert cart_payment_2

        # Test that we only allow a VERIFIED card in commando mode
        with RuntimeContextManager(
            STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY, [1], runtime_setter
        ), RuntimeContextManager(VERIFY_CARD_IN_COMMANDO_MODE, True, runtime_setter):
            cart_payment_3 = self._test_cart_payment_legacy_payment_creation(
                client=client,
                stripe_customer_id=provider_account_id,
                stripe_card_id=provider_card_id,
                amount=800,
                merchant_country=CountryCode.US,
                dd_stripe_card_id=stripe_card.id,
                commando_mode=True,
            )
            assert cart_payment_3

        # Now make the stripe card we have used cannot be verified by invalid stripe charges created by this card
        async def fail_all_stripe_charges_for_card(
            app_context: AppContext, dd_stripe_card_id: int
        ):

            stmt = (
                stripe_charges.table.update()
                .where(stripe_charges.card_id == dd_stripe_card_id)
                .values(
                    status=LegacyStripeChargeStatus.FAILED,
                    updated_at=datetime.now(timezone.utc),
                )
            )

            await app_context.payin_maindb.master().execute(stmt)

        event_loop.run_until_complete(
            fail_all_stripe_charges_for_card(app_context, stripe_card.id)
        )

        # After invalidated all previous charges to failed, this attempt should fail when we don't allow
        # commando mode on card without previous successful charges
        with RuntimeContextManager(
            STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY, [1], runtime_setter
        ), RuntimeContextManager(VERIFY_CARD_IN_COMMANDO_MODE, True, runtime_setter):
            expected_failed_response = self._create_cart_payment_legacy_get_raw_response(
                client=client,
                stripe_customer_id=provider_account_id,
                stripe_card_id=provider_card_id,
                amount=900,
                merchant_country=CountryCode.US,
                dd_stripe_card_id=stripe_card.id,
            )
            assert expected_failed_response.status_code == 500

        # But this one will pass, if we allow all card in commando mode WITHOUT verifying
        with RuntimeContextManager(
            STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY, [1], runtime_setter
        ), RuntimeContextManager(VERIFY_CARD_IN_COMMANDO_MODE, False, runtime_setter):
            cart_payment_4 = self._test_cart_payment_legacy_payment_creation(
                client=client,
                stripe_customer_id=provider_account_id,
                stripe_card_id=provider_card_id,
                amount=1000,
                merchant_country=CountryCode.US,
                dd_stripe_card_id=stripe_card.id,
                commando_mode=True,
            )
            assert cart_payment_4

        total, result = event_loop.run_until_complete(commando_processor.recoup())
        assert total == 3
        assert len(result) == total
        assert cart_payment_3["amount"] != cart_payment_2["amount"]
        assert cart_payment_4["amount"] != cart_payment_3["amount"]
        assert cart_payment_4["amount"] != cart_payment_2["amount"]
        assert {
            int(cart_payment_2["amount"]),
            int(cart_payment_3["amount"]),
            int(cart_payment_4["amount"]),
        } == {result[0][1], result[1][1], result[2][1]}

    def test_payment_provider_error(
        self, stripe_api: StripeAPISettings, client: TestClient
    ):
        stripe_api.enable_outbound()

        payer = self._test_payer_creation(client)
        payment_method = self._test_payment_method_creation(
            client, payer, "tok_chargeCustomerFail"
        )

        request_body = self._get_cart_payment_create_request(payer, payment_method)
        self._test_cart_payment_creation_error(
            client, request_body, 400, "payin_43", False
        )

        # Resubmit same request
        self._test_cart_payment_creation_error(
            client, request_body, 400, "payin_43", False
        )

    def test_cart_payment_validation(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
    ):
        # Cart payment creation
        # Currency
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 750, True
        )
        request_body["currency"] = "coffee beans"
        self._test_cart_payment_creation_error(
            client, request_body, 422, "request_validation_error", False
        )

        # Country
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 750, True
        )
        request_body["payment_country"] = "SM"
        self._test_cart_payment_creation_error(
            client, request_body, 422, "request_validation_error", False
        )

        # Amount
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 0, True
        )
        self._test_cart_payment_creation_error(
            client, request_body, 422, "request_validation_error", False
        )
        request_body["amount"] = "-1"
        self._test_cart_payment_creation_error(
            client, request_body, 422, "request_validation_error", False
        )

        # Statement descriptor
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 0, True
        )
        request_body["payer_statement_description"] = "01234567891123456789212"
        self._test_cart_payment_creation_error(
            client, request_body, 422, "request_validation_error", False
        )

        # Client description over 1000 too long
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 0, True
        )
        request_body[
            "client_description"
        ] = """
            #order_cart_adjustment# Hi Test Name,

            This email is to confirm that we have edited your DoorDash order.
            The new total cost of your order is $15.00 which includes
            all taxes and fees.

            Please note, you might see a refund for the
            original order amount and a new, separate charge reflecting the final
            adjusted order total of $15.00 in your account.

            You can verify the final order total charge in your account by
            visiting www.DoorDash.com and following these steps:
                1. Click the 3 stacked bars to access the site menu.
                2. Click Orders from the menu list.
                3. Click on the relevant order to review the details, including order total.

            The refund of your original order total and the updated final order total
            charge can take between 5-7 business days to complete, depending on your
            bank’s processing times.

            Thanks again for ordering with DoorDash.
            Please feel free to contact us if there’s anything else we can help with.

            Best,
            Varun
            DoorDash Customer Care
            support.doordash.com"
            """
        self._test_cart_payment_creation_error(
            client, request_body, 422, "request_validation_error", False
        )

        # Cart payment update
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 750, True
        )
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=750,
            delay_capture=False,
        )
        request_body = self._get_cart_payment_update_request(
            cart_payment=cart_payment,
            amount=1000,
            client_description=f"{cart_payment['client_description']}-updated",
        )
        self._test_adjust_cart_payment_not_found_error(
            client, cart_payment, request_body, 404, "payin_61", False
        )
        request_body = self._get_cart_payment_update_request(
            cart_payment=cart_payment,
            amount=-1,
            client_description=f"{cart_payment['client_description']}-updated",
        )
        self._test_cart_payment_update_error(
            client, cart_payment, request_body, 422, "request_validation_error", False
        )

    def test_legacy_payment_card_use_errors(
        self,
        stripe_api: StripeAPISettings,
        stripe_customer: StripeCustomer,
        client: TestClient,
    ):
        stripe_api.enable_outbound()

        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_chargeDeclined",
            amount=900,
            merchant_country=CountryCode.US,
        )
        self._test_legacy_cart_payment_creation_error(
            client, request_body, 400, "payin_43", False
        )

        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_chargeDeclinedInsufficientFunds",
            amount=900,
            merchant_country=CountryCode.US,
        )
        self._test_legacy_cart_payment_creation_error(
            client, request_body, 400, "payin_43", False
        )

        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_chargeDeclinedFraudulent",
            amount=900,
            merchant_country=CountryCode.US,
        )
        self._test_legacy_cart_payment_creation_error(
            client, request_body, 400, "payin_43", False
        )

        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_chargeDeclinedExpiredCard",
            amount=900,
            merchant_country=CountryCode.US,
        )
        self._test_legacy_cart_payment_creation_error(
            client, request_body, 400, "payin_44", False
        )

        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_chargeDeclinedProcessingError",
            amount=900,
            merchant_country=CountryCode.US,
        )
        self._test_legacy_cart_payment_creation_error(
            client, request_body, 400, "payin_45", False
        )

        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_chargeDeclinedIncorrectCvc",
            amount=900,
            merchant_country=CountryCode.US,
        )
        self._test_legacy_cart_payment_creation_error(
            client, request_body, 400, "payin_49", False
        )

        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_mastercard",
            amount=30,
            merchant_country=CountryCode.US,
        )
        self._test_legacy_cart_payment_creation_error(
            client, request_body, 400, "payin_64", False
        )

    def test_legacy_payment_client_description(
        self,
        stripe_api: StripeAPISettings,
        stripe_customer: StripeCustomer,
        client: TestClient,
    ):
        stripe_api.enable_outbound()

        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_mastercard",
            amount=900,
            merchant_country=CountryCode.US,
        )
        request_body[
            "client_description"
        ] = """
            #order_cart_adjustment# Hi Test Name,

            This email is to confirm that we have edited your DoorDash order.
            The new total cost of your order is $15.00 which includes
            all taxes and fees.

            Please note, you might see a refund for the
            original order amount and a new, separate charge reflecting the final
            adjusted order total of $15.00 in your account.

            You can verify the final order total charge in your account by
            visiting www.DoorDash.com and following these steps:
                1. Click the 3 stacked bars to access the site menu.
                2. Click Orders from the menu list.
                3. Click on the relevant order to review the details, including order total.

            The refund of your original order total and the updated final order total
            charge can take between 5-7 business days to complete, depending on your
            bank’s processing times.

            Thanks again for ordering with DoorDash.
            Please feel free to contact us if there’s anything else we can help with.

            Best,
            Varun
            DoorDash Customer Care
            support.doordash.com"
        """

        response = client.post("/payin/api/v0/cart_payments", json=request_body)
        assert response.status_code == 201
        cart_payment = response.json()
        assert (
            cart_payment["client_description"]
            == request_body["client_description"][:1000]
        )

    def test_legacy_card_use(
        self,
        stripe_api: StripeAPISettings,
        stripe_customer: StripeCustomer,
        client: TestClient,
    ):
        # PAYIN-140: Use "None" for stripe_customer_id
        self._test_cart_payment_legacy_payment_creation(
            client=client,
            stripe_customer_id="None",
            stripe_card_id="pm_card_mastercard",
            amount=900,
            merchant_country=CountryCode.US,
        )

    @pytest.mark.parametrize("enable_cart_locking", [True, False])
    def test_legacy_payment(
        self,
        stripe_api: StripeAPISettings,
        stripe_customer: StripeCustomer,
        client: TestClient,
        runtime_setter: RuntimeSetter,
        enable_cart_locking: bool,
    ):
        stripe_api.enable_outbound()
        runtime_setter.set(
            "payin/feature-flags/enable_payin_cart_payment_update_locking.bool",
            enable_cart_locking,
        )

        # Client provides Stripe customer ID and Stripe customer ID, instead of payer_id and payment_method_id
        cart_payment = self._test_cart_payment_legacy_payment_creation(
            client=client,
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_mastercard",
            amount=900,
            merchant_country=CountryCode.US,
        )

        # Adjustment for case where legacy payment was initially used
        self._test_legacy_cart_payment_adjustment(
            client=client,
            cart_payment=cart_payment,
            charge_id=cart_payment["dd_charge_id"],
            amount=100,
            original_amount=900,
        )

        # Adjustment, but down
        self._test_legacy_cart_payment_adjustment(
            client=client,
            cart_payment=cart_payment,
            charge_id=cart_payment["dd_charge_id"],
            amount=-250,
            original_amount=1000,
        )

        # Adjustment. Up but cart payment not found
        self._test_legacy_update_cart_payment_not_found_error(
            client=client,
            cart_payment=cart_payment,
            charge_id=self._get_random_charge_id(cart_payment["dd_charge_id"]),
            amount=2500,
            original_amount=1000,
            payin_error_code="payin_65",
        )

        # Cancel
        self._test_cart_payment_legacy_cancel(
            client=client, charge_id=cart_payment["dd_charge_id"]
        )

        # Split payment use in v0 api
        split_payment = {
            "payout_account_id": "acct_1FKYqjDpmxeDAkcx",  # Pre-seeded stripe sandbox testing account
            "application_fee_amount": 100,
        }
        cart_payment = self._test_cart_payment_legacy_payment_creation(
            client=client,
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_mastercard",
            split_payment=split_payment,
            amount=860,
            merchant_country=CountryCode.US,
        )

    def test_get_legacy_cart_payment(
        self,
        stripe_api: StripeAPISettings,
        stripe_customer: StripeCustomer,
        client: TestClient,
    ):
        stripe_api.enable_outbound()

        # Client provides Stripe customer ID and Stripe customer ID, instead of payer_id and payment_method_id
        cart_payment = self._test_cart_payment_legacy_payment_creation(
            client=client,
            stripe_customer_id=stripe_customer.id,
            stripe_card_id="pm_card_mastercard",
            amount=900,
            merchant_country=CountryCode.US,
        )

        self._test_cart_payment_legacy_payment_get(
            client=client, dd_charge_id=cart_payment["dd_charge_id"]
        )

    def test_get_cart_payment(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        app_context: AppContext,
    ):
        stripe_api.enable_outbound()

        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=500,
            delay_capture=False,
        )

        self._test_cart_payment_get(client=client, cart_payment_id=cart_payment["id"])

    def test_get_cart_payment_not_found(
        self, stripe_api: StripeAPISettings, client: TestClient, app_context: AppContext
    ):
        stripe_api.enable_outbound()
        self._test_cart_payment_get_not_found(
            client=client, cart_payment_id=str(uuid.uuid4())
        )

    def test_list_legacy_cart_payment(
        self,
        stripe_api: StripeAPISettings,
        stripe_customer: StripeCustomer,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        client: TestClient,
    ):
        stripe_api.enable_outbound()

        # Getting the inital cart payment list for a consumer id
        inital_response = self._list_cart_payment_get_legacy_response(
            client=client,
            dd_consumer_id="1",
            created_at_gte=None,
            created_at_lte=None,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert inital_response.status_code == 200
        inital_cart_payment_list = inital_response.json()
        assert inital_cart_payment_list
        assert isinstance(inital_cart_payment_list["data"], List)
        initial_cart_payment_count = inital_cart_payment_list["count"]

        # Creating a new cart payment
        test_client_description: str = str(uuid.uuid4())
        provider_account_id = payer["payment_gateway_provider_customers"][0][
            "payment_provider_customer_id"
        ]

        provider_card_id = payment_method["payment_gateway_provider_details"][
            "payment_method_id"
        ]
        cart_payment = self._test_cart_payment_legacy_payment_creation(
            client=client,
            stripe_customer_id=provider_account_id,
            stripe_card_id=provider_card_id,
            amount=900,
            merchant_country=CountryCode.US,
            client_description=test_client_description,
        )
        assert cart_payment

        # Getting the final cart payment list for a consumer id
        final_response = self._list_cart_payment_get_legacy_response(
            client=client,
            dd_consumer_id="1",
            created_at_gte=None,
            created_at_lte=None,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert final_response.status_code == 200
        final_cart_payment_list = final_response.json()
        assert final_cart_payment_list
        assert final_cart_payment_list["data"]
        final_cart_payment_count = final_cart_payment_list["count"]
        assert final_cart_payment_count - initial_cart_payment_count == 1
        created_cart_payment = next(
            filter(
                lambda cart_payment: cart_payment["client_description"]
                == test_client_description,
                final_cart_payment_list["data"],
            ),
            None,
        )
        assert created_cart_payment

    def test_list_cart_payments(
        self, client: TestClient, payer: Dict[str, Any], payment_method: Dict[str, Any]
    ):
        initial_response = self._list_cart_payment_response(
            client=client,
            payer_id=payer["id"],
            created_at_gte=None,
            created_at_lte=None,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert initial_response.status_code == 200
        cart_payment_list = initial_response.json()
        assert cart_payment_list
        inital_count = cart_payment_list["count"]

        test_client_description = str(uuid.uuid4())
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=600,
            delay_capture=False,
            client_description=test_client_description,
        )
        assert cart_payment

        response = self._list_cart_payment_response(
            client=client,
            payer_id=payer["id"],
            created_at_gte=None,
            created_at_lte=None,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert response.status_code == 200
        cart_payment_list = response.json()
        assert cart_payment_list
        assert cart_payment_list["count"] - inital_count == 1
        retrieve_created_cart_payment = next(
            filter(
                lambda cart_payment: cart_payment["client_description"]
                == test_client_description,
                cart_payment_list["data"],
            ),
            None,
        )
        assert retrieve_created_cart_payment

    def test_list_cart_payments_by_payer_reference_id(
        self, client: TestClient, payer: Dict[str, Any], payment_method: Dict[str, Any]
    ):
        dd_stripe_customer_id = payer["legacy_dd_stripe_customer_id"]
        initial_response = self._list_cart_payment_response(
            client=client,
            payer_reference_id=dd_stripe_customer_id,
            payer_reference_id_type=PayerReferenceIdType.LEGACY_DD_STRIPE_CUSTOMER_ID,
            created_at_gte=None,
            created_at_lte=None,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert initial_response.status_code == 200
        cart_payment_list = initial_response.json()
        assert cart_payment_list
        inital_count = cart_payment_list["count"]

        test_client_description = str(uuid.uuid4())
        cart_payment = self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=600,
            delay_capture=False,
            client_description=test_client_description,
        )
        assert cart_payment

        response = self._list_cart_payment_response(
            client=client,
            payer_reference_id=dd_stripe_customer_id,
            payer_reference_id_type=PayerReferenceIdType.LEGACY_DD_STRIPE_CUSTOMER_ID,
            created_at_gte=None,
            created_at_lte=None,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert response.status_code == 200
        cart_payment_list = response.json()
        assert cart_payment_list
        assert cart_payment_list["count"] - inital_count == 1
        retrieve_created_cart_payment = next(
            filter(
                lambda cart_payment: cart_payment["client_description"]
                == test_client_description,
                cart_payment_list["data"],
            ),
            None,
        )
        assert retrieve_created_cart_payment
