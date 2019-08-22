from typing import Dict, Any, Type, Optional

from app.commons.providers.stripe.stripe_models import PaymentMethod, StripeBaseModel

# Mapping for a stripe "object" field to Internal Stripe Object Pydantic class
# Reference: https://stripe.com/docs/api/events/object#event_object-data-object
EVENT_TYPE_STRIPE_MODEL_MAPPING: Dict[str, Type[StripeBaseModel]] = {
    PaymentMethod._STRIPE_OBJECT_NAME: PaymentMethod
}


class InternalStripeModelMappingError(Exception):
    pass


def create_from_mapped_type(type_name: str, obj: Dict[str, Any]):
    klass: Optional[Type[StripeBaseModel]] = EVENT_TYPE_STRIPE_MODEL_MAPPING.get(
        type_name, None
    )
    if not klass:
        raise InternalStripeModelMappingError(
            f"No valid mapping found for given type_name {type_name}"
        )
    return klass(**obj)
