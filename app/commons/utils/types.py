from enum import Enum


# todo: this needs to be moved to commons/types.py
class PaymentProvider(str, Enum):
    """
    Enum definition of supported payment gateway providers.
    """

    STRIPE = "stripe"
