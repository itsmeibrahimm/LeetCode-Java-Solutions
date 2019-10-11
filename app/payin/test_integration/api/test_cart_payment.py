import random
from asyncio import AbstractEventLoop

import pytest
import uuid
from starlette.testclient import TestClient
from typing import Any, Optional, Dict

from app.commons.context.app_context import AppContext
from app.commons.providers.stripe.stripe_models import Customer as StripeCustomer
from app.commons.types import CountryCode
from app.commons.operational_flags import (
    STRIPE_COMMANDO_MODE_BOOLEAN,
    STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY,
)
from app.conftest import StripeAPISettings, RuntimeSetter, RuntimeContextManager


# Since this test requires a sequence of calls to stripe in order to set up a payment intent
# creation attempt, we need to use the actual test stripe system.  As a result this test class
# is marked as external.  The stripe simulator does not return the correct result since it does
# persist state.
from app.payin.core.cart_payment.processor import CommandoProcessor
from app.payin.test_integration.integration_utils import build_commando_processor


@pytest.mark.external
class TestCartPayment:
    @pytest.fixture
    def payer(self, stripe_api: StripeAPISettings, client: TestClient):
        stripe_api.enable_outbound()
        return self._test_payer_creation(client)

    def _get_payer_create_request(self):
        unique_value = str(uuid.uuid4())
        request_body = {
            "dd_payer_id": "1",
            "payer_type": "store",
            "email": f"{unique_value}@doordash.com",
            "country": "US",
            "description": f"{unique_value} description",
        }
        return request_body

    def _test_payer_creation(self, client: TestClient) -> Dict[str, Any]:
        request_body = self._get_payer_create_request()
        response = client.post("/payin/api/v1/payers", json=request_body)
        assert response.status_code == 201

        payer = response.json()
        assert payer
        assert payer["id"]
        assert payer["payer_type"] == request_body["payer_type"]
        assert payer["country"] == request_body["country"]
        assert payer["dd_payer_id"] == request_body["dd_payer_id"]
        assert payer["description"] == request_body["description"]
        assert payer["created_at"]
        assert payer["updated_at"]
        assert payer["deleted_at"] is None
        assert payer["payment_gateway_provider_customers"]
        assert len(payer["payment_gateway_provider_customers"]) == 1
        provider_customer = payer["payment_gateway_provider_customers"][0]
        assert provider_customer["payment_provider"] == "stripe"
        assert provider_customer["payment_provider_customer_id"]
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
        assert response.status_code == 201
        payment_method = response.json()
        assert payment_method
        assert payment_method["id"]
        assert (
            payment_method["payment_gateway_provider_details"]["payment_provider"]
            == "stripe"
        )
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
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        request_body = {
            "payer_id": payer["id"],
            "amount": amount,
            "payment_country": "US",
            "currency": "usd",
            "payment_method_id": payment_method["id"],
            "delay_capture": delay_capture,
            "client_description": f"{payer['id']} description",
            "payer_statement_description": f"{payer['id'][0:10]} statement",
            "correlation_ids": {"reference_id": "123", "reference_type": "3"},
        }

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
    ) -> Dict[str, Any]:
        # No payer_id or payment_method_id.  Instead we use legacy_payment.
        request_body = {
            "amount": amount,
            "currency": "usd",
            "delay_capture": True,
            "client_description": f"{stripe_customer_id} description",
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
                "dd_stripe_card_id": "1",
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
            "payer_id": cart_payment["payer_id"],
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

    def _test_cart_payment_legacy_payment_creation(
        self,
        client: TestClient,
        stripe_customer_id: str,
        stripe_card_id: str,
        amount: int,
        merchant_country: CountryCode,
        split_payment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_body = self._get_cart_payment_create_legacy_payment_request(
            stripe_customer_id=stripe_customer_id,
            stripe_card_id=stripe_card_id,
            amount=amount,
            split_payment=split_payment,
            merchant_country=merchant_country,
        )

        response = client.post("/payin/api/v0/cart_payments", json=request_body)
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
        return cart_payment

    def _test_cart_payment_creation(
        self,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        amount: int,
        delay_capture: bool,
        split_payment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, amount, delay_capture, split_payment
        )
        response = client.post("/payin/api/v1/cart_payments", json=request_body)
        assert response.status_code == 201
        cart_payment = response.json()
        assert cart_payment
        assert cart_payment["id"]
        assert cart_payment["amount"] == request_body["amount"]
        assert cart_payment["payer_id"] == payer["id"]
        assert cart_payment["payment_method_id"] == request_body["payment_method_id"]
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

    def _test_legacy_update_cart_payment_not_found_error(
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
        self._test_cart_payment_error(
            client,
            f"/payin/api/v0/cart_payments/{str(charge_id)}/adjust",
            request_body,
            404,
            "payin_61",
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
        return body

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

        # Adjust down again
        updated_cart_payment = self._test_cart_payment_adjustment(
            client=client, cart_payment=updated_cart_payment, amount=390
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
    def test_cart_payment_creation(
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
        stripe_api.enable_outbound()
        runtime_setter.set(STRIPE_COMMANDO_MODE_BOOLEAN, commando_mode)

        amounts = (500, 600, 560)

        # Success case: intent created, not captured yet
        self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=500,
            delay_capture=True,
        )

        # Success case: intent created, auto captured
        self._test_cart_payment_creation(
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=600,
            delay_capture=False,
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
        )

        # Other payer cannot use some else's payment method for cart payment creation
        with RuntimeContextManager(STRIPE_COMMANDO_MODE_BOOLEAN, False, runtime_setter):
            other_payer = payer = self._test_payer_creation(client)

        request_body = self._get_cart_payment_create_request(
            other_payer, payment_method
        )
        self._test_cart_payment_creation_error(
            client, request_body, 403, "payin_23", False
        )

        if commando_mode:
            with RuntimeContextManager(
                STRIPE_COMMANDO_MODE_BOOLEAN, False, runtime_setter
            ):
                commando_processor: CommandoProcessor = build_commando_processor(
                    app_context=app_context
                )
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
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        runtime_setter: RuntimeSetter,
        app_context: AppContext,
        event_loop: AbstractEventLoop,
    ):
        stripe_api.enable_outbound()
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

        # Client provides Stripe customer ID and Stripe customer ID, instead of payer_id and payment_method_id
        with RuntimeContextManager(
            STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY, [1], runtime_setter
        ):
            cart_payment = self._test_cart_payment_legacy_payment_creation(
                client=client,
                stripe_customer_id=provider_account_id,
                stripe_card_id=provider_card_id,
                amount=700,
                merchant_country=CountryCode.US,
            )
            assert cart_payment

        cart_payment = self._test_cart_payment_legacy_payment_creation(
            client=client,
            stripe_customer_id=provider_account_id,
            stripe_card_id=provider_card_id,
            amount=900,
            merchant_country=CountryCode.US,
        )

        assert cart_payment

        commando_processor: CommandoProcessor = build_commando_processor(
            app_context=app_context
        )
        total, result = event_loop.run_until_complete(commando_processor.recoup())

        assert result[0][1] == 700

        assert total == 1

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
            client, request_body, 500, "payin_40", False
        )

        # Resubmit same request
        self._test_cart_payment_creation_error(
            client, request_body, 500, "payin_40", False
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

    def test_legacy_payment(
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
