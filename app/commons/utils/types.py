from enum import Enum


class PaymentProvider(str, Enum):
    """
    Enum definition of supported payment gateway providers.
    """

    STRIPE = "stripe"
