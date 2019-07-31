import pytest
from pydantic import ValidationError
from app.commons.providers.stripe_models import CreatePaymentIntent


class TestPaymentIntent:
    def test_create(self):
        create = CreatePaymentIntent(amount=200, currency="USD")
        assert create.dict(skip_defaults=True) == {"amount": 200, "currency": "USD"}

        # type aliases are supported
        create = CreatePaymentIntent(amount=200, currency="USD", customer="cust_399")
        # but type is erased
        create.customer = "not a customer"

        # enum
        create = CreatePaymentIntent(
            amount=222, currency="CAD", capture_method="automatic"
        )
        assert create.capture_method == "automatic", "validates enum"

        # data validation is done
        with pytest.raises(ValidationError, match=r"\bcapture_method\b"):
            CreatePaymentIntent(amount=222, currency="CAD", capture_method="invalid")

        # dictionaries are translated to nested objects
        create = CreatePaymentIntent(
            amount=222,
            currency="CAD",
            transfer_data={"destination": "acct_1234", "amount": 123},
        )
        assert create.transfer_data
        assert create.transfer_data.destination == "acct_1234"
        assert create.transfer_data.amount == 123
