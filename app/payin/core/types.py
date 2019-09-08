from enum import Enum
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel

from app.commons.types import CountryCode


MixedUuidStrType = Union[UUID, str]


class LegacyPaymentInfo(BaseModel):
    """
    Legacy payment information for DSJ backward compatibility.
    """

    dd_consumer_id: Optional[str] = None
    dd_stripe_card_id: Optional[str] = None
    dd_charge_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_payment_method_id: Optional[str] = None
    stripe_card_id: Optional[str] = None


# https://pydantic-docs.helpmanual.io/#self-referencing-models
LegacyPaymentInfo.update_forward_refs()


class LegacyPaymentMethodInfo(BaseModel):
    """
    Legacy payment method information for DSJ backward compatibility.
    """

    country: CountryCode = CountryCode.US
    dd_consumer_id: Optional[str]
    stripe_customer_id: Optional[str]


class PayerIdType(str, Enum):
    """
    Enum definition of payer id type. This is used in most of payin API endpoints for
    backward compatibility purpose to identify the type of input payer_id.
    """

    PAYER_ID = "payer_id"
    DD_CONSUMER_ID = "dd_consumer_id"
    DD_STRIPE_CUSTOMER_SERIAL_ID = "dd_stripe_customer_serial_id"  # used for payer APIs
    STRIPE_CUSTOMER_ID = "stripe_customer_id"  # used for payer/payment_method APIs


class PaymentMethodIdType(str, Enum):
    """
    Enum definition of payment method id type. This is used in most of payin API endpoints for
    backward compatibility purpose to identify the type of input payment_method_id.
    """

    PAYMENT_METHOD_ID = "payment_method_id"
    DD_STRIPE_CARD_SERIAL_ID = "dd_stripe_card_id"  # used for payment_methods APIs
    STRIPE_PAYMENT_METHOD_ID = (
        "stripe_payment_method_id"
    )  # used for payment_methods APIs


class PaymentMethodObjectType(str, Enum):
    """
    Enum definition of  payment method object type. This is used in payment_method APIs
    to identify the object type.
    """

    PAYMENT_METHOD = "payment_method"
    SOURCE = "source"
    CARD = "card"


class DisputePayerIdType(str, Enum):
    """
    Enum definition of payer id type for a dispute. This is used in Dispute API endpoints to identify
    type of input payer id
    """

    DD_PAYMENT_PAYER_ID = "dd_payer_id"
    STRIPE_CUSTOMER_ID = "stripe_customer_id"


class DisputePaymentMethodIdType(str, Enum):
    """
    Enum definition of payment method id type for a dispute. This is used in Dispute API endpoints to identify
    type of input payment method id
    """

    DD_PAYMENT_METHOD_ID = PaymentMethodIdType.PAYMENT_METHOD_ID
    STRIPE_PAYMENT_METHOD_ID = PaymentMethodIdType.STRIPE_PAYMENT_METHOD_ID
