from app.commons.providers.stripe.stripe_models import Event, PaymentMethod
from app.commons.providers.stripe.stripe_object_mapping import create_from_mapped_type


class TestStripeObjectMapping:
    def test_create_from_mapped_type(self, sample_payment_method_webhook):
        event = Event(**sample_payment_method_webhook)

        object = create_from_mapped_type(event.resource_type, event.data_object)
        assert isinstance(object, PaymentMethod)
