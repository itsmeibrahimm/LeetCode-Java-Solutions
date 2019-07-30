from enum import Enum

from app.commons.error.errors import PaymentError


payin_error_message_maps = {
    "payin_1": "Invalid data types. Please verify your input again!",
    "payin_2": "Invalid data types. Please verify your input again!",
    "payin_3": "Payer not found. Please ensure your payer_id is correct",
    "payin_4": "Payer not found. Please ensure your payer_id is correct",
    "payin_5": "Invalid data types. Please verify your input again!",
}


class PayinErrorCode(str, Enum):
    PAYER_CREATION_INVALID_DATA = "payin_1"
    PAYER_READ_INVALID_DATA = "payin_2"
    PAYER_READ_NOT_FOUND = "payin_3"
    PAYER_UPDATE_NOT_FOUND = "payin_4"
    PAYER_UPDATE_DB_ERROR_INVALID_DATA = "payin_5"


class PayerReadError(PaymentError):
    pass


class PayerCreationError(PaymentError):
    pass


class PayerUpdateError(PaymentError):
    pass


class PaymentMethodCreateError(PaymentError):
    pass


class PaymentMethodReadError(PaymentError):
    pass


class PaymentMethodDeleteError(PaymentError):
    pass
