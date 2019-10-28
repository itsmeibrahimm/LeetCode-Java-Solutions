from enum import Enum
from typing import Optional

from app.commons.core.errors import PaymentError
from app.payin.core.cart_payment.types import IntentStatus

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
    "payin_11": "Data I/O error. Please retry again!",
    "payin_12": "Error returned from Payment Provider.",
    "payin_13": "No such customer",
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
    "payin_43": "Cannot create payment.  Payment card declined.",
    "payin_44": "Cannot create payment.  Payment card expired.",
    "payin_45": "Cannot create payment.  Payment card cannot be processed.",
    "payin_46": "Cannot create payment.  Payment card number incorrect.",
    "payin_47": "An error occurred attempting your payment request.  Please try again later.",
    "payin_60": "Invalid data provided. Please verify parameters.",
    "payin_61": "Cart Payment not found.  Please ensure your cart_payment_id is correct.",
    "payin_62": "Cart Payment not accessible by caller.",
    "payin_63": "Cart Payment data is invalid.",
    "payin_64": "The provided amount is not valid.",
    "payin_100": "Dispute not found. Please ensure your dispute_id is correct",
    "payin_101": "Data I/O error. Please retry again!",
    "payin_102": "Invalid data types. Please verify your input again!",
    "payin_103": "No parameters provides. Provide verify your input",
    "payin_104": "The given payer_id does not have a payer associated to it",
    "payin_105": "The given payment_method_id does not have a payment_method associated to it",
    "payin_106": "No id parameters provides. Please verify your input",
    "payin_107": "More than 1 id parameter provided. Please verify your input",
    "payin_108": "Error returned from Payment Provider.",
    "payin_109": "The given dispute_id does not have a stripe_card associated to it",
    "payin_110": "The given dispute_id does not have a consumer_charge associated to it's stripe charge",
    "payin_111": "Error. Empty data returned from DB after update",
    "payin_800": "API not accessible/usable in commando mode",
}


class PayinErrorCode(str, Enum):
    CART_PAYMENT_CREATE_INVALID_DATA = "payin_60"
    CART_PAYMENT_NOT_FOUND = "payin_61"
    CART_PAYMENT_OWNER_MISMATCH = "payin_62"
    CART_PAYMENT_DATA_INVALID = "payin_63"
    CART_PAYMENT_AMOUNT_INVALID = "payin_64"
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
    PAYER_UPDATE_DB_ERROR = "payin_11"
    PAYER_READ_STRIPE_ERROR = "payin_12"
    PAYER_READ_STRIPE_ERROR_NOT_FOUND = "payin_13"
    PAYMENT_INTENT_CREATE_STRIPE_ERROR = "payin_40"
    PAYMENT_INTENT_CAPTURE_STRIPE_ERROR = "payin_41"
    PAYMENT_INTENT_ADJUST_REFUND_ERROR = "payin_42"
    PAYMENT_INTENT_CREATE_CARD_DECLINED_ERROR = "payin_43"
    PAYMENT_INTENT_CREATE_CARD_EXPIRED_ERROR = "payin_44"
    PAYMENT_INTENT_CREATE_CARD_PROCESSING_ERROR = "payin_45"
    PAYMENT_INTENT_CREATE_CARD_INCORRECT_NUMBER_ERROR = "payin_46"
    PAYMENT_INTENT_CREATE_ERROR = "payin_47"
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
    DISPUTE_LIST_NO_PARAMETERS = "payin_103"
    DISPUTE_NO_PAYER_FOR_PAYER_ID = "payin_104"
    DISPUTE_NO_STRIPE_CARD_FOR_PAYMENT_METHOD_ID = "payin_105"
    DISPUTE_LIST_NO_ID_PARAMETERS = "payin_106"
    DISPUTE_LIST_MORE_THAN_ID_ONE_PARAMETER = "payin_107"
    DISPUTE_UPDATE_STRIPE_ERROR = "payin_108"
    DISPUTE_NO_STRIPE_CARD_FOR_STRIPE_ID = "payin_109"
    DISPUTE_NO_CONSUMER_CHARGE_FOR_STRIPE_DISPUTE = "payin_110"
    DISPUTE_UPDATE_DB_ERROR = "payin_111"
    COMMANDO_DISABLED_ENDPOINT = "payin_800"


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
    def __init__(
        self,
        error_code: PayinErrorCode,
        retryable: bool,
        provider_charge_id: Optional[str],
        provider_error_code: Optional[str],
        provider_decline_code: Optional[str],
        has_provider_error_details: bool,
    ):
        super(CartPaymentCreateError, self).__init__(
            error_code=error_code, retryable=retryable
        )
        self.provider_error_code = provider_error_code
        self.provider_decline_code = provider_decline_code
        self.provider_charge_id = provider_charge_id
        self.has_provider_error_details = has_provider_error_details


class CartPaymentReadError(PayinError):
    pass


class CartPaymentUpdateError(PayinError):
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


class DisputeUpdateError(PayinError):
    pass


###########################################################
# Provider Errors                                         #
###########################################################
class BaseProviderError(Exception):
    def __init__(self, orig_error: Exception) -> None:
        self.orig_error = orig_error
        super().__init__()


class ProviderError(BaseProviderError):
    pass


class UnhandledProviderError(BaseProviderError):
    """
    An unknown error provided by the provider
    """

    pass


class InvalidProviderRequestError(BaseProviderError):
    pass


class ProviderPaymentIntentUnexpectedStatusError(InvalidProviderRequestError):
    """
    Model an error raised from pgp when desired action cannot be applied to target pgp object
    """

    provider_payment_intent_status: str
    pgp_payment_intent_status: IntentStatus

    def __init__(
        self,
        provider_payment_intent_status: str,
        pgp_payment_intent_status: IntentStatus,
        original_error: Exception,
    ):
        super().__init__(original_error)
        self.provider_payment_intent_status = provider_payment_intent_status
        self.pgp_payment_intent_status = pgp_payment_intent_status


class CommandoModeShortCircuit(PayinError):
    pass


###########################################################
# Commando Errors                                         #
###########################################################
class CommandoProcessingError(Exception):
    pass
