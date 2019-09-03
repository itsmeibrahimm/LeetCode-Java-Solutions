import uuid

import pytest
from starlette.testclient import TestClient


# Since this test requires a sequence of calls to stripe in order to set up a payment intent
# creation attempt, we need to use the actual test stripe system.  As a result this test class
# is marked as external.  The stripe simulator does not return the correct result since it does
# persist state.
@pytest.mark.external
class TestCartPayment:
    def _get_payer_create_request(self):
        unique_value = str(uuid.uuid4())
        request_body = {
            "dd_payer_id": unique_value,
            "payer_type": "marketplace",
            "email": f"{unique_value}@doordash.com",
            "country": "US",
            "description": f"{unique_value} description",
        }
        return request_body

    def _get_payer_payment_method_request(self, payer):
        request_body = {
            "payer_id": payer["id"],
            "payment_gateway": "stripe",
            "token": "tok_mastercard",
            # "legacy_payment_info": {
            #     "stripe_customer_id": payer["payment_gateway_provider_customers"][0][
            #         "payment_provider_customer_id"
            #     ]
            # },
        }
        return request_body

    def _get_cart_payment_create_request(
        self,
        payer,
        payment_method,
        amount=500,
        capture_method="manual",
        idempotency_key=None,
    ):
        request_body = {
            "payer_id": payer["id"],
            "amount": amount,
            "payer_country": "US",
            "payment_country": "US",
            "currency": "USD",
            "payment_method_id": payment_method["id"],
            "capture_method": capture_method,
            "client_description": f"{payer['id']} description",
            "payer_statement_description": f"{payer['id'][0:10]} statement",
            "metadata": {
                "reference_id": 123,
                "ct_reference_id": 5,
                "type": "OrderCart",
            },
        }

        if not idempotency_key:
            request_body["idempotency_key"] = str(uuid.uuid4())

        return request_body

    def _get_cart_payment_update_request(
        self, cart_payment, amount, client_description, idempotency_key=None
    ):
        request_body = {
            "amount": amount,
            "payer_id": cart_payment["payer_id"],
            "client_description": client_description,
        }
        idempotency = idempotency_key if idempotency_key else str(uuid.uuid4())
        request_body["idempotency_key"] = idempotency
        return request_body

    def _test_payer_creation(self, stripe_api, client):
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

    def _test_payment_method_creation(self, stripe_api, client, payer):
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

    def _test_cart_payment_creation(
        self, stripe_api, client, payer, payment_method, amount, capture_method
    ):
        request_body = self._get_cart_payment_create_request(
            payer, payment_method, amount, capture_method
        )
        response = client.post("/payin/api/v1/cart_payments", json=request_body)
        assert response.status_code == 201
        cart_payment = response.json()
        print(cart_payment)
        assert cart_payment
        assert cart_payment["id"]
        assert cart_payment["amount"] == request_body["amount"]
        assert cart_payment["payer_id"] == payer["id"]
        assert cart_payment["payment_method_id"] == request_body["payment_method_id"]
        assert cart_payment["capture_method"] == request_body["capture_method"]
        assert cart_payment["cart_metadata"]
        metadata = cart_payment["cart_metadata"]
        assert metadata["reference_id"] == request_body["metadata"]["reference_id"]
        assert (
            metadata["ct_reference_id"] == request_body["metadata"]["ct_reference_id"]
        )
        assert metadata["type"] == request_body["metadata"]["type"]
        assert cart_payment["client_description"] == request_body["client_description"]
        statement_description = cart_payment["payer_statement_description"]
        assert statement_description == request_body["payer_statement_description"]
        assert cart_payment["legacy_payment"] is None
        assert cart_payment["split_payment"] is None
        assert cart_payment["created_at"]
        assert cart_payment["updated_at"]
        assert cart_payment["deleted_at"] is None
        return cart_payment

    def _test_cart_payment_creation_error(
        self,
        stripe_api,
        client,
        payer,
        payment_method,
        expected_http_status_status_code,
        expected_body_error_code,
        expected_retryable,
    ):
        request_body = self._get_cart_payment_create_request(payer, payment_method)
        response = client.post("/payin/api/v1/cart_payments", json=request_body)
        body = response.json()
        assert response.status_code == expected_http_status_status_code
        assert "error_code" in body
        assert body["error_code"] == expected_body_error_code
        assert "error_message" in body
        assert "retryable" in body
        assert body["retryable"] == expected_retryable

    def _test_cart_payment_adjustment(self, stripe_api, client, cart_payment, amount):
        request_body = self._get_cart_payment_update_request(
            cart_payment=cart_payment,
            amount=amount,
            client_description=f"{cart_payment['client_description']}-updated",
        )
        response = client.post(
            f"/payin/api/v1/cart_payments/{str(cart_payment['id'])}/adjust",
            json=request_body,
        )
        # print(response)
        body = response.json()
        # print("**** Body")
        # print(body)
        assert response.status_code == 200
        assert body["id"] == cart_payment["id"]
        assert body["amount"] == request_body["amount"]
        assert body["payer_id"] == cart_payment["payer_id"]
        assert body["payment_method_id"] == cart_payment["payment_method_id"]
        assert body["capture_method"] == cart_payment["capture_method"]
        assert body["cart_metadata"] == cart_payment["cart_metadata"]
        assert body["client_description"] == request_body["client_description"]
        statement_description = body["payer_statement_description"]
        assert statement_description == cart_payment["payer_statement_description"]

    def test_cart_payment(self, stripe_api, client: TestClient):
        stripe_api.enable_outbound()

        payer = self._test_payer_creation(stripe_api=stripe_api, client=client)
        payment_method = self._test_payment_method_creation(
            stripe_api=stripe_api, client=client, payer=payer
        )

        # Success case: intent created, not captured yet
        cart_payment = self._test_cart_payment_creation(
            stripe_api=stripe_api,
            client=client,
            payer=payer,
            payment_method=payment_method,
            amount=500,
            capture_method="manual",
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
            amount=500,
            capture_method="auto",
        )

        # Other payer cannot use some else's payment method
        other_payer = payer = self._test_payer_creation(stripe_api, client)
        self._test_cart_payment_creation_error(
            stripe_api, client, other_payer, payment_method, 403, "payin_23", False
        )
