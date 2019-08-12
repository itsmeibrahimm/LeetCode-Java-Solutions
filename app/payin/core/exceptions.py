from enum import Enum

from app.commons.error.errors import PaymentError


payin_error_message_maps = {
    "payin_1": "Invalid data types. Please verify your input again!",
    "payin_2": "Invalid data types. Please verify your input again!",
    "payin_3": "Payer not found. Please ensure your payer_id is correct",
    "payin_4": "Payer not found. Please ensure your payer_id is correct",
    "payin_5": "Invalid data types. Please verify your input again!",
    "payin_6": "Invalid payer type",
    "payin_7": "Error returned from Payment Provider.",
    "payin_20": "Invalid data types. Please verify your input again!",
    "payin_21": "Data I/O error. Please retry again!",
    "payin_22": "Invalid input payment method type!",
    "payin_23": "payer_id and payment_method_id mismatch! Please ensure payer owns the payment_method!!",
    "payin_24": "Payment method not found. Please ensure your payment_method_id is correct",
    "payin_25": "Data I/O error. Please retry again!",
    "payin_26": "Error returned from Payment Provider. Please make sure your token is correct!",
    "payin_27": "Invalid input. Please ensure valid id is provided!",
    "payin_28": "Error returned from Payment Provider. Please make sure your payment_method_id is correct!",
    "payin_29": "Data I/O error. Please retry again!",
}


class PayinErrorCode(str, Enum):
    PAYER_CREATE_INVALID_DATA = "payin_1"
    PAYER_READ_INVALID_DATA = "payin_2"
    PAYER_READ_NOT_FOUND = "payin_3"
    PAYER_UPDATE_NOT_FOUND = "payin_4"
    PAYER_UPDATE_DB_ERROR_INVALID_DATA = "payin_5"
    PAYER_UPDATE_INVALID_PAYER_TYPE = "payin_6"
    PAYER_CREATE_STRIPE_ERROR = "payin_7"
    PAYMENT_METHOD_CREATE_INVALID_DATA = "payin_20"
    PAYMENT_METHOD_CREATE_DB_ERROR = "payin_21"
    PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE = "payin_22"
    PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH = "payin_23"
    PAYMENT_METHOD_GET_NOT_FOUND = "payin_24"
    PAYMENT_METHOD_GET_DB_ERROR = "payin_25"
    PAYMENT_METHOD_CREATE_STRIPE_ERROR = "payin_26"
    PAYMENT_METHOD_CREATE_INVALID_INPUT = "payin_27"
    PAYMENT_METHOD_DELETE_STRIPE_ERROR = "payin_28"
    PAYMENT_METHOD_DELETE_DB_ERROR = "payin_29"


###########################################################
# Payer Errors                                            #
###########################################################
class PayerReadError(PaymentError):
    pass


class PayerCreationError(PaymentError):
    pass


class PayerUpdateError(PaymentError):
    pass


###########################################################
# PaymentMethod Errors                                    #
###########################################################
class PaymentMethodCreateError(PaymentError):
    pass


class PaymentMethodReadError(PaymentError):
    pass


class PaymentMethodDeleteError(PaymentError):
    pass


class PaymentMethodListError(PaymentError):
    pass
