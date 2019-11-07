import pytest
from pydantic import ValidationError
from app.commons.providers.stripe.stripe_models import (
    StripeCreatePaymentIntentRequest,
    Event,
    PaymentIntent,
)


class TestPaymentIntent:
    def test_create(self):
        create = StripeCreatePaymentIntentRequest(amount=200, currency="USD")
        assert create.dict(skip_defaults=True) == {"amount": 200, "currency": "USD"}

        # type aliases are supported
        create = StripeCreatePaymentIntentRequest(
            amount=200, currency="USD", customer="cust_399"
        )
        # but type is erased
        create.customer = "not a customer"

        # enum
        create = StripeCreatePaymentIntentRequest(
            amount=222, currency="CAD", capture_method="automatic"
        )
        assert create.capture_method == "automatic", "validates enum"

        # dictionaries are translated to nested objects
        create = StripeCreatePaymentIntentRequest(
            amount=222,
            currency="CAD",
            transfer_data={"destination": "acct_1234", "amount": 123},
        )
        assert create.transfer_data
        assert create.transfer_data.destination == "acct_1234"
        assert create.transfer_data.amount == 123

    @pytest.mark.skip(
        "Type change required for stripe call to work - tbd if this can be changed back"
    )
    def test_enum_validation(self):
        # data validation is done
        with pytest.raises(ValidationError, match=r"\bcapture_method\b"):
            StripeCreatePaymentIntentRequest(
                amount=222, currency="CAD", capture_method="invalid"
            )

    def test_payment_intent_deserialization(self):
        data = {
            "id": "pi_1FbxgeAFJYNIHuofvqmXEbyO",
            "object": "payment_intent",
            "allowed_source_types": ["card"],
            "amount": 2000,
            "amount_capturable": 0,
            "amount_received": 50,
            "application": None,
            "application_fee_amount": None,
            "canceled_at": None,
            "cancellation_reason": None,
            "capture_method": "manual",
            "charges": {
                "object": "list",
                "data": [
                    {
                        "id": "ch_1FbxgeAFJYNIHuofpde4jOAc",
                        "object": "charge",
                        "amount": 2000,
                        "amount_refunded": 1950,
                        "application": None,
                        "application_fee": None,
                        "application_fee_amount": None,
                        "balance_transaction": "txn_1FbxgxAFJYNIHuof6G9enDLJ",
                        "billing_details": {
                            "address": {
                                "city": None,
                                "country": None,
                                "line1": None,
                                "line2": None,
                                "postal_code": None,
                                "state": None,
                            },
                            "email": None,
                            "name": None,
                            "phone": None,
                        },
                        "captured": True,
                        "created": 1573081996,
                        "currency": "usd",
                        "customer": None,
                        "description": None,
                        "destination": None,
                        "dispute": None,
                        "disputed": False,
                        "failure_code": None,
                        "failure_message": None,
                        "fraud_details": {},
                        "invoice": None,
                        "livemode": False,
                        "metadata": {},
                        "on_behalf_of": None,
                        "order": None,
                        "outcome": {
                            "network_status": "approved_by_network",
                            "reason": None,
                            "risk_level": "normal",
                            "risk_score": 46,
                            "seller_message": "Payment complete.",
                            "type": "authorized",
                        },
                        "paid": True,
                        "payment_intent": "pi_1FbxgeAFJYNIHuofvqmXEbyO",
                        "payment_method": "pm_1FbxgdAFJYNIHuof60EMshLd",
                        "payment_method_details": {
                            "card": {
                                "brand": "visa",
                                "checks": {
                                    "address_line1_check": None,
                                    "address_postal_code_check": None,
                                    "cvc_check": None,
                                },
                                "country": "US",
                                "exp_month": 11,
                                "exp_year": 2020,
                                "fingerprint": "AETpvknLxADPObzc",
                                "funding": "credit",
                                "installments": None,
                                "last4": "4242",
                                "network": "visa",
                                "network_transaction_id": "AETpvknLxADPObzc",
                                "three_d_secure": None,
                                "wallet": None,
                            },
                            "type": "card",
                        },
                        "receipt_email": None,
                        "receipt_number": None,
                        "receipt_url": "https://pay.stripe.com/receipts/acct_16qVpAAFJYNIHuof/ch_1FbxgeAFJYNIHuofpde4jOAc/rcpt_G8E8oIy42gF9lb37NJ8CiJF7ie1FKNq",
                        "refunded": False,
                        "refunds": {
                            "object": "list",
                            "data": [
                                {
                                    "id": "re_1FbxgxAFJYNIHuofrEOwRY5y",
                                    "object": "refund",
                                    "amount": 1950,
                                    "balance_transaction": "txn_1FbxgxAFJYNIHuof2ExiCsj4",
                                    "charge": "ch_1FbxgeAFJYNIHuofpde4jOAc",
                                    "created": 1573082015,
                                    "currency": "usd",
                                    "metadata": {},
                                    "payment_intent": "pi_1FbxgeAFJYNIHuofvqmXEbyO",
                                    "payment_method_details": {
                                        "card": {
                                            "acquirer_reference_number": None,
                                            "acquirer_reference_number_status": "unavailable",
                                        },
                                        "type": "card",
                                    },
                                    "reason": None,
                                    "receipt_number": None,
                                    "source_transfer_reversal": None,
                                    "status": "succeeded",
                                    "transfer_reversal": None,
                                }
                            ],
                            "has_more": False,
                            "total_count": 1,
                            "url": "/v1/charges/ch_1FbxgeAFJYNIHuofpde4jOAc/refunds",
                        },
                        "review": None,
                        "shipping": None,
                        "source": None,
                        "source_transfer": None,
                        "statement_descriptor": None,
                        "statement_descriptor_suffix": None,
                        "status": "succeeded",
                        "transfer_data": None,
                        "transfer_group": None,
                    }
                ],
                "has_more": False,
                "total_count": 1,
                "url": "/v1/charges?payment_intent=pi_1FbxgeAFJYNIHuofvqmXEbyO",
            },
            "client_secret": "pi_1FbxgeAFJYNIHuofvqmXEbyO_secret_WAmPnJLw25wPcZ4MXAfUEP46l",
            "confirmation_method": "automatic",
            "created": 1573081996,
            "currency": "usd",
            "customer": None,
            "description": None,
            "invoice": None,
            "last_payment_error": None,
            "livemode": False,
            "metadata": {},
            "next_action": None,
            "next_source_action": None,
            "on_behalf_of": None,
            "payment_method": "pm_1FbxgdAFJYNIHuof60EMshLd",
            "payment_method_options": {
                "card": {"installments": None, "request_three_d_secure": "automatic"}
            },
            "payment_method_types": ["card"],
            "receipt_email": None,
            "review": None,
            "setup_future_usage": None,
            "shipping": None,
            "source": None,
            "statement_descriptor": None,
            "statement_descriptor_suffix": None,
            "status": "succeeded",
            "transfer_data": None,
            "transfer_group": None,
        }

        assert PaymentIntent.parse_obj(data)


class TestEvent:
    def test_get_resource_type(
        self, sample_payment_method_webhook, sample_customer_subscription
    ):
        event = Event(**sample_payment_method_webhook)
        resource_type = event.resource_type
        assert resource_type == "payment_method"

        event = Event(**sample_customer_subscription)
        resource_type = event.resource_type
        assert resource_type == "subscription"

    def test_get_event_type(
        self, sample_payment_method_webhook, sample_customer_subscription
    ):
        event = Event(**sample_payment_method_webhook)
        event_type = event.event_type
        assert event_type == "attached"

        event = Event(**sample_customer_subscription)
        event_type = event.event_type
        assert event_type == "deleted"
