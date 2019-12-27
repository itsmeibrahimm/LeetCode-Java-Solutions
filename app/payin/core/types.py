from enum import Enum
from typing import Optional, Union, Dict, Any, NewType
from uuid import UUID

from pydantic import BaseModel

MixedUuidStrType = Union[UUID, str]

PgpPaymentMethodResourceId = NewType("PgpPaymentMethodResourceId", str)
PgpPayerResourceId = NewType("PgpPayerResourceId", str)


class LegacyPaymentInfo(BaseModel):
    """
    Legacy payment information for DSJ backward compatibility.
    """

    dd_consumer_id: int
    dd_stripe_card_id: int
    dd_country_id: int
    dd_additional_payment_info: Optional[Dict[str, Any]] = None
    stripe_customer_id: PgpPayerResourceId
    stripe_card_id: PgpPaymentMethodResourceId


class PayerIdType(str, Enum):
    """
    (V0 only) Enum definition of payer id type. This is used in most of payin API endpoints for
    backward compatibility purpose to identify the type of input payer_id.
    """

    PAYER_ID = "payer_id"
    DD_CONSUMER_ID = "dd_consumer_id"
    DD_STRIPE_CUSTOMER_SERIAL_ID = "dd_stripe_customer_serial_id"  # used for payer APIs
    STRIPE_CUSTOMER_ID = "stripe_customer_id"  # used for payer/payment_method APIs


class PayerReferenceIdType(str, Enum):
    """
    Enum definition of payer reference id type. This is used in most of payin API endpoints for
    backward compatibility purpose to identify the type of input payer_id.
    """

    PAYER_ID = "payer_id"
    DD_CONSUMER_ID = "dd_consumer_id"
    DD_STRIPE_CUSTOMER_ID = "dd_stripe_customer_id"  # used for payer APIs
    DD_DRIVE_STORE_ID = "dd_drive_store_id"
    DD_DRIVE_MERCHANT_ID = "dd_drive_merchant_id"
    DD_DRIVE_BUSINESS_ID = "dd_drive_business_id"
    STRIPE_CUSTOMER_ID = "stripe_customer_id"  # used for payer/payment_method APIs


class PaymentMethodIdType(str, Enum):
    """
    Enum definition of payment method id type. This is used in most of payin API endpoints for
    backward compatibility purpose to identify the type of input payment_method_id.
    """

    PAYMENT_METHOD_ID = "payment_method_id"
    DD_STRIPE_CARD_ID = "dd_stripe_card_id"  # used for payment_methods APIs
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
