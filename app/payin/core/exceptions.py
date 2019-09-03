from enum import Enum

from app.commons.error.errors import PaymentError


payin_error_message_maps = {
    "payin_1": "Invalid data types. Please verify your input again!",
    "payin_2": "Error returned from Payment Provider.",
    "payin_3": "Payer already exists.",
    "payin_4": "Invalid data types. Please verify your input again!",
    "payin_5": "Payer not found. Please ensure your payer_id is correct",
    "payin_6": "Data I/O error. Please retry again!",
    "payin_7": "Payer not found. Please ensure your payer_id is correct",
    "payin_8": "Invalid data types. Please verify your input again!",
    "payin_9": "Invalid payer type",
    "payin_10": "Error returned from Payment Provider.",
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
    "payin_40": "Error returned from Payment Provider. Please make sure your payer_id, payment_method_id are correct!",
    "payin_41": "Error returned from Payment Provider. Please verify parameters of capture.",
    "payin_42": "Cannot refund previous charge for amount increase.",
    "payin_60": "Invalid data provided. Please verify parameters.",
    "payin_61": "Cart Payment not found.  Please ensure your cart_payment_id is correct.",
    "payin_62": "Cart Payment not accessible by caller.",
    "payin_100": "Dispute not found. Please ensure your dispute_id is correct",
    "payin_101": "Data I/O error. Please retry again!",
    "payin_102": "Invalid data types. Please verify your input again!",
}


class PayinErrorCode(str, Enum):
    CART_PAYMENT_CREATE_INVALID_DATA = "payin_60"
    CART_PAYMENT_NOT_FOUND = "payin_61"
    CART_PAYMENT_OWNER_MISMATCH = "payin_62"
    PAYER_CREATE_INVALID_DATA = "payin_1"
    PAYER_CREATE_STRIPE_ERROR = "payin_2"
    PAYER_CREATE_PAYER_ALREADY_EXIST = "payin_3"
    PAYER_READ_INVALID_DATA = "payin_4"
    PAYER_READ_NOT_FOUND = "payin_5"
    PAYER_READ_DB_ERROR = "payin_6"
    PAYER_UPDATE_NOT_FOUND = "payin_7"
    PAYER_UPDATE_DB_ERROR_INVALID_DATA = "payin_8"
    PAYER_UPDATE_INVALID_PAYER_TYPE = "payin_9"
    PAYER_UPDATE_STRIPE_ERROR = "payin_10"
    PAYMENT_INTENT_CREATE_STRIPE_ERROR = "payin_40"
    PAYMENT_INTENT_CAPTURE_STRIPE_ERROR = "payin_41"
    PAYMENT_INTENT_ADJUST_REFUND_ERROR = "payin_42"
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
    DISPUTE_NOT_FOUND = "payin_100"
    DISPUTE_READ_DB_ERROR = "payin_101"
    DISPUTE_READ_INVALID_DATA = "payin_102"


# TODO Enhance errors to allow us to declare here the response codes they should map to
# (e.g. if it is permission related and should result in 403, or data existence related
# and should map to 404, etc).
class PayinError(PaymentError):
    """
    Base exception class for payin. This is base class that can be inherited by
    each business operation layer with corresponding sub error class and
    raise to application layers.  Provides automatic supplying of error message
    based on provided code.
    """

    def __init__(self, error_code: PayinErrorCode, retryable: bool):
        """
        Base Payin exception class.

        :param error_code: payin service predefined client-facing error codes.
        :param retryable: identify if the error is retryable or not.
        """
        super(PayinError, self).__init__(
            error_code.value, payin_error_message_maps[error_code.value], retryable
        )


###########################################################
# Payer Errors                                            #
###########################################################
class PayerReadError(PayinError):
    pass


class PayerCreationError(PayinError):
    pass


class PayerUpdateError(PayinError):
    pass


###########################################################
# PaymentMethod Errors                                    #
###########################################################
class PaymentMethodCreateError(PayinError):
    pass


class PaymentMethodReadError(PayinError):
    pass


class PaymentMethodDeleteError(PayinError):
    pass


class PaymentMethodListError(PayinError):
    pass


###########################################################
# CartPayment Errors                                      #
###########################################################
class CartPaymentCreateError(PayinError):
    pass


class CartPaymentReadError(PayinError):
    pass


###########################################################
# PaymentCharge Errors                                      #
###########################################################
class PaymentChargeRefundError(PayinError):
    pass


###########################################################
# PaymentIntent Errors                                      #
###########################################################
class PaymentIntentCaptureError(PayinError):
    pass


class PaymentIntentCancelError(PayinError):
    pass


class PaymentIntentRefundError(PayinError):
    pass


class PaymentIntentNotInRequiresCaptureState(Exception):
    pass


class PaymentIntentCouldNotBeUpdatedError(Exception):
    pass


class PaymentIntentConcurrentAccessError(Exception):
    pass


###########################################################
# StripeDispute Errors                                      #
###########################################################
class DisputeReadError(PayinError):
    pass
