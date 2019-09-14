import pytest
import uuid
from starlette.testclient import TestClient
from typing import Any, Optional, Dict
from app.conftest import StripeAPISettings

# Since this test requires a sequence of calls to stripe in order to set up a payment intent
# creation attempt, we need to use the actual test stripe system.  As a result this test class
# is marked as external.  The stripe simulator does not return the correct result since it does
# persist state.
@pytest.mark.external
class TestCartPayment:
    @pytest.fixture
    def payer(self, stripe_api: StripeAPISettings, client: TestClient):
        stripe_api.enable_outbound()
        return self._test_payer_creation(stripe_api, client)

    def _get_payer_create_request(self):
        unique_value = str(uuid.uuid4())
        request_body = {
            "dd_payer_id": "1",
            "payer_type": "marketplace",
            "email": f"{unique_value}@doordash.com",
            "country": "US",
            "description": f"{unique_value} description",
        }
        return request_body

    def _test_payer_creation(
        self, stripe_api: StripeAPISettings, client: TestClient
    ) -> Dict[str, Any]:
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
        return self._test_payment_method_creation(stripe_api, client, payer)

    def _get_payer_payment_method_request(
        self, payer: Dict[str, Any]
    ) -> Dict[str, Any]:
        request_body = {
            "payer_id": payer["id"],
            "payment_gateway": "stripe",
            "token": "tok_mastercard",
        }
        return request_body

    def _test_payment_method_creation(
        self, stripe_api: StripeAPISettings, client: TestClient, payer: Dict[str, Any]
    ) -> Dict[str, Any]:
        request_body = self._get_payer_payment_method_request(payer)
        response = client.post("/payin/api/v1/payment_methods", json=request_body)
        assert response.status_code == 201
        payment_method = response.json()
        assert payment_method
        assert payment_method["id"]
        assert payment_method["payment_provider"] == "stripe"
        assert payment_method["card"]
        assert payment_method["card"]["last4"]
        assert payment_method["card"]["exp_year"]
        assert payment_method["card"]["exp_month"]
        assert payment_method["card"]["fingerprint"]
        assert payment_method["card"]["active"]
        assert payment_method["card"]["country"]
        assert payment_method["card"]["brand"]
        assert payment_method["card"]["payment_provider_card_id"]
        assert payment_method["payer_id"] == payer["id"]
        assert payment_method["type"] == "card"
        assert payment_method["dd_consumer_id"] is None
        assert payment_method["payment_provider_customer_id"] is None  # TODO
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
            "cart_metadata": {
                "reference_id": "123",
                "reference_type": "5",
                "type": "OrderCart",
            },
        }

        if not idempotency_key:
            request_body["idempotency_key"] = str(uuid.uuid4())

        return request_body

    def _get_cart_payment_create_legacy_payment_request(
        self,
        legacy_stripe_customer_id: str,
        legacy_stripe_payment_method_id: str,
        amount: int = 500,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        # No payer_id or payment_method_id.  Instead we use legacy_payment.
        request_body = {
            "amount": amount,
            "currency": "usd",
            "delay_capture": True,
            "client_description": f"{legacy_stripe_customer_id} description",
            "payer_statement_description": f"{legacy_stripe_customer_id}",
            "payer_country": "US",
            "payment_country": "US",
            "cart_metadata": {
                "reference_id": "123",
                "reference_type": "5",
                "type": "OrderCart",
            },
            "legacy_payment": {
                "stripe_customer_id": legacy_stripe_customer_id,
                "stripe_payment_method_id": legacy_stripe_payment_method_id,
                "dd_country_id": 1,
                "dd_consumer_id": 1,
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
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        request_body = {
            "amount": amount,
            "payer_id": cart_payment["payer_id"],
            "client_description": client_description,
        }
        idempotency = idempotency_key if idempotency_key else str(uuid.uuid4())
        request_body["idempotency_key"] = idempotency
        return request_body

    def _test_cart_payment_legacy_payment_creation(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        legacy_stripe_customer_id: str,
        legacy_stripe_payment_method_id: str,
        amount: int,
    ) -> Dict[str, Any]:
        request_body = self._get_cart_payment_create_legacy_payment_request(
            legacy_stripe_customer_id, legacy_stripe_payment_method_id, amount
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
        assert cart_payment["cart_metadata"]
        metadata = cart_payment["cart_metadata"]
        assert metadata["reference_id"] == request_body["cart_metadata"]["reference_id"]
        assert (
            metadata["reference_type"]
            == request_body["cart_metadata"]["reference_type"]
        )
        assert metadata["type"] == request_body["cart_metadata"]["type"]
        assert cart_payment["client_description"] == request_body["client_description"]
        statement_description = cart_payment["payer_statement_description"]
        assert statement_description == request_body["payer_statement_description"]
        assert cart_payment["split_payment"] is None
        assert cart_payment["created_at"]
        assert cart_payment["updated_at"]
        assert cart_payment["deleted_at"] is None
        assert cart_payment["dd_charge_id"]
        assert type(cart_payment["dd_charge_id"]) is int
        return cart_payment

    def _test_cart_payment_creation(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
        amount: int,
        delay_capture: bool,
    ) -> Dict[str, Any]:
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, amount, delay_capture
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
        assert cart_payment["cart_metadata"]
        metadata = cart_payment["cart_metadata"]
        assert metadata["reference_id"] == request_body["cart_metadata"]["reference_id"]
        assert (
            metadata["reference_type"]
            == request_body["cart_metadata"]["reference_type"]
        )
        assert metadata["type"] == request_body["cart_metadata"]["type"]
        assert cart_payment["client_description"] == request_body["client_description"]
        statement_description = cart_payment["payer_statement_description"]
        assert statement_description == request_body["payer_statement_description"]
        assert cart_payment["split_payment"] is None
        assert cart_payment["created_at"]
        assert cart_payment["updated_at"]
        assert cart_payment["deleted_at"] is None
        return cart_payment

    def _test_cart_payment_error(
        self,
        stripe_api: StripeAPISettings,
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

    def _test_legacy_cart_payment_adjustment(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        cart_payment: Dict[str, Any],
        charge_id: int,
        amount: int,
    ) -> None:
        request_body = self._get_cart_payment_update_request(
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
        assert body["amount"] == request_body["amount"]
        assert body["payer_id"] == cart_payment["payer_id"]
        assert body["payment_method_id"] == cart_payment["payment_method_id"]
        assert body["delay_capture"] == cart_payment["delay_capture"]
        assert body["cart_metadata"] == cart_payment["cart_metadata"]
        assert body["client_description"] == request_body["client_description"]
        statement_description = body["payer_statement_description"]
        assert statement_description == cart_payment["payer_statement_description"]

    def _test_cart_payment_creation_error(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        request_body: Dict[str, Any],
        expected_http_status_status_code: int,
        expected_body_error_code: str,
        expected_retryable: bool,
    ) -> None:
        self._test_cart_payment_error(
            stripe_api,
            client,
            "/payin/api/v1/cart_payments",
            request_body,
            expected_http_status_status_code,
            expected_body_error_code,
            expected_retryable,
        )

    def _test_cart_payment_update_error(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        cart_payment: Dict[str, Any],
        request_body: Dict[str, Any],
        expected_http_status_status_code: int,
        expected_body_error_code: str,
        expected_retryable: bool,
    ) -> None:
        self._test_cart_payment_error(
            stripe_api,
            client,
            f"/payin/api/v1/cart_payments/{str(cart_payment['id'])}/adjust",
            request_body,
            expected_http_status_status_code,
            expected_body_error_code,
            expected_retryable,
        )

    def _test_cart_payment_adjustment(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        cart_payment: Dict[str, Any],
        amount: int,
    ) -> None:
        request_body = self._get_cart_payment_update_request(
            cart_payment=cart_payment,
            amount=amount,
            client_description=f"{cart_payment['client_description']}-updated",
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
        assert body["cart_metadata"] == cart_payment["cart_metadata"]
        assert body["client_description"] == request_body["client_description"]
        statement_description = body["payer_statement_description"]
        assert statement_description == cart_payment["payer_statement_description"]

    def test_cart_payment_use(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
    ):
        stripe_api.enable_outbound()

        # Success case: intent created, not captured yet
        cart_payment = self._test_cart_payment_creation(
            stripe_api=stripe_api,
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=500,
            delay_capture=True,
        )

        # Order cart adjustment
        self._test_cart_payment_adjustment(
            stripe_api=stripe_api, client=client, cart_payment=cart_payment, amount=800
        )
        # self._test_cart_payment_adjustment(
        #     stripe_api=stripe_api, client=client, cart_payment=cart_payment, amount=300
        # )

        # Success case: intent created, auto captured
        cart_payment = self._test_cart_payment_creation(
            stripe_api=stripe_api,
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=600,
            delay_capture=False,
        )

        # Other payer cannot use some else's payment method
        other_payer = payer = self._test_payer_creation(stripe_api, client)
        request_body = self._get_cart_payment_create_request(
            other_payer, payment_method
        )
        self._test_cart_payment_creation_error(
            stripe_api, client, request_body, 403, "payin_23", False
        )

    def test_cart_payment_validation(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
    ):
        # Cart payment creation
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 750, True
        )
        request_body["currency"] = "coffee beans"
        self._test_cart_payment_creation_error(
            stripe_api, client, request_body, 422, "request_validation_error", False
        )

        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 750, True
        )
        request_body["payment_country"] = "SM"
        self._test_cart_payment_creation_error(
            stripe_api, client, request_body, 422, "request_validation_error", False
        )

        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 0, True
        )
        self._test_cart_payment_creation_error(
            stripe_api, client, request_body, 422, "request_validation_error", False
        )
        request_body["amount"] = "-1"
        self._test_cart_payment_creation_error(
            stripe_api, client, request_body, 422, "request_validation_error", False
        )

        # Cart payment update
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, 750, True
        )
        cart_payment = self._test_cart_payment_creation(
            stripe_api=stripe_api,
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=750,
            delay_capture=False,
        )
        request_body = self._get_cart_payment_update_request(
            cart_payment=cart_payment,
            amount=-1,
            client_description=f"{cart_payment['client_description']}-updated",
        )
        self._test_cart_payment_update_error(
            stripe_api,
            client,
            cart_payment,
            request_body,
            422,
            "request_validation_error",
            False,
        )

    def test_legacy_payment(
        self,
        stripe_api: StripeAPISettings,
        client: TestClient,
        payer: Dict[str, Any],
        payment_method: Dict[str, Any],
    ):
        stripe_api.enable_outbound()

        # Use payer, payment method api calls to seed data into legacy table.  It would be better to
        # create directly in legacy system without creating corresponding records in the new tables since
        # that is a more realistic case, but there is not yet an easy way to set this up.
        provider_account_id = payer["payment_gateway_provider_customers"][0][
            "payment_provider_customer_id"
        ]

        provider_card_id = payment_method["card"]["payment_provider_card_id"]

        # Client provides Stripe customer ID and Stripe customer ID, instead of payer_id and payment_method_id
        cart_payment = self._test_cart_payment_legacy_payment_creation(
            stripe_api=stripe_api,
            client=client,
            legacy_stripe_customer_id=provider_account_id,
            legacy_stripe_payment_method_id=provider_card_id,
            amount=900,
        )

        # Adjustment for case where legacy payment was initially used
        self._test_legacy_cart_payment_adjustment(
            stripe_api=stripe_api,
            client=client,
            cart_payment=cart_payment,
            charge_id=cart_payment["dd_charge_id"],
            amount=1000,
        )
