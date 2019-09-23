import pytest
from pydantic import ValidationError
from app.commons.providers.stripe.stripe_models import (
    StripeCreatePaymentIntentRequest,
    Event,
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
