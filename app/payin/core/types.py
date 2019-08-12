from enum import Enum
from typing import Optional

from pydantic import BaseModel


class LegacyPaymentInfo(BaseModel):
    """
    Legacy payment information for DSJ backward compatibility.
    """

    dd_consumer_id: Optional[str]
    stripe_customer_id: Optional[str]
    charge_id: Optional[str]


# https://pydantic-docs.helpmanual.io/#self-referencing-models
LegacyPaymentInfo.update_forward_refs()


class PayerIdType(str, Enum):
    """
    Enum definition of payer id type. This is used in most of payin API endpoints for
    backward compatibility purpose to identify the type of input payer_id.
    """

    DD_PAYMENT_PAYER_ID = "dd_payer_id"
    # used for payer/payment_method APIs
    STRIPE_CUSTOMER_ID = "stripe_customer_id"
    # used for payer APIs
    STRIPE_CUSTOMER_SERIAL_ID = "stripe_customer_serial_id"
    DD_CONSUMER_ID = "dd_consumer_id"


class PaymentMethodIdType(str, Enum):
    """
    Enum definition of payment method id type. This is used in most of payin API endpoints for
    backward compatibility purpose to identify the type of input payment_method_id.
    """

    PAYMENT_PAYMENT_METHOD_ID = "dd_payment_method_id"
    # used for payment_methods APIs
    STRIPE_PAYMENT_METHOD_ID = "stripe_payment_method_id"
    # used for payment_methods APIs
    STRIPE_CARD_SERIAL_ID = "stripe_card_serial_id"


class PaymentMethodObjectType(str, Enum):
    """
    Enum definition of  payment method object type. This is used in payment_method APIs
    to identify the object type.
    """

    PAYMENT_METHOD = "payment_method"
    SOURCE = "source"
    CARD = "card"
