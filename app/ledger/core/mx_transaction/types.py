from enum import Enum


class MxTransactionType(str, Enum):
    """
    Enum definition of mx_transaction type.
    """

    MERCHANT_DELIVERY = "merchant_delivery"
    STORE_PAYMENT = "store_payment"
    DELIVERY_ERROR = "delivery_error"
    DELIVERY_RECEIPT = "delivery_receipt"
    MICRO_DEPOSIT = "micro_deposit"


class MxLedgerType(str, Enum):
    """
    Enum definition of mx_ledger type.
    """

    MICRO_DEPOSIT = "micro_deposit"
    MANUAL = "manual"


class MxLedgerStateType(str, Enum):
    """
    Enum definition of mx_ledger state.
    """

    OPEN = "open"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    ROLLED = "rolled"
    REVERSED = "reversed"
