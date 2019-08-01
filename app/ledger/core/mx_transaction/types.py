from enum import Enum


class MxTransactionType(str, Enum):
    """
    Enum definition of mx_transaction type.
    """

    MERCHANT_DELIVERY = "merchant_delivery"
    STORE_PAYMENT = "store_payment"
    DELIVERY_ERROR = "delivery_error"
    DELIVERY_RECEIPT = "delivery_receipt"
