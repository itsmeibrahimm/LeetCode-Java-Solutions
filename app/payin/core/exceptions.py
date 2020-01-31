from enum import Enum
from typing import NewType, Optional

from app.commons.core.errors import PaymentError
from app.commons.utils import validation
from app.payin.core.cart_payment.types import IntentStatus

# Kept here for testing and backward compatibility, will be removed soon.
_payin_error_message_maps = {
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
    "payin_14": "Data I/O error. Please retry again!",
    "payin_15": "Data I/O error. Please retry again!",
    "payin_16": "No such customer",
    "payin_17": "Error returned from Payment Provider.",
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
    "payin_30": "No Stripe Card associated to the payment method",
    "payin_31": "Sorting method not supported for list payment methods",
    "payin_32": "Invalid payer type for list payment method",
    "payin_33": "Data I/O error. Please retry again!",
    "payin_34": "Mismatch in correlation ids for payer",
    "payin_40": "Error returned from Payment Provider. Please make sure your payer_id, payment_method_id are correct!",
    "payin_41": "Error returned from Payment Provider. Please verify parameters of capture.",
    "payin_42": "Cannot refund previous charge for amount increase.",
    "payin_43": "Cannot create payment.  Payment card declined.",
    "payin_44": "Cannot create payment.  Payment card expired.",
    "payin_45": "Cannot create payment.  Payment card cannot be processed.",
    "payin_46": "Cannot create payment.  Payment card number incorrect.",
    "payin_47": "An error occurred attempting your payment request.  Please try again later.",
    "payin_48": "Invalid split payment payout account.  This is account is not configured correctly for payment use.",
    "payin_49": "Cannot create payment.  Payment card cvc incorrect.",
    "payin_50": "Cannot create payment.  Payment creation failed.",
    "payin_51": "Unable to establish payment method for cross country payment.",
    "payin_52": "Unable to create payment due to invalid provider payment method data.",
    "payin_60": "Invalid data provided. Please verify parameters.",
    "payin_61": "Cart Payment not found.  Please ensure your cart_payment_id is correct.",
    "payin_62": "Cart Payment not accessible by caller.",
    "payin_63": "Cart Payment data is invalid.",
    "payin_64": "The provided amount is not valid.",
    "payin_65": "Cart Payment not found for given dd_charge_id. Likely the charge "
    "was created in DSJ the update was requested against Payment Service",
    "payin_66": "Payment method used to create cart payment was not found",
    "payin_67": "Another process is attempting to modify the same cart payment.  Please try again later.",
    "payin_68": "The idempotency key is invalid.",
    "payin_69": "Data I/O error. Please retry again!",
    "payin_70": "No corresponding payer found for given payer_reference_id.",
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
    "payin_120": "Data I/O error. Please retry again!",
    "payin_800": "API not accessible/usable in commando mode",
    "not_implemented": "This API is not implemented!",
    "invalid_payer_reference_id": "Invalid input of payer_id and payer_reference_id",
}


_Retryable = NewType("_Retryable", bool)
SHOULD_RETRY = _Retryable(True)
NO_RETRY = _Retryable(False)


class PayinErrorCode(str, Enum):
    """
    Enumeration of all Pay-In Service pre-defined error codes.
    """

    _message: str
    _retryable: bool

    CART_PAYMENT_CREATE_INVALID_DATA = (
        "payin_60",
        NO_RETRY,
        "Invalid data provided. Please verify parameters.",
    )
    CART_PAYMENT_NOT_FOUND = (
        "payin_61",
        NO_RETRY,
        "Cart Payment not found.  Please ensure your cart_payment_id is correct.",
    )
    CART_PAYMENT_NOT_FOUND_FOR_CHARGE_ID = (
        "payin_65",
        NO_RETRY,
        "Cart Payment not found for given dd_charge_id. Likely the charge "
        "was created in DSJ the update was requested against Payment Service",
    )
    CART_PAYMENT_OWNER_MISMATCH = (
        "payin_62",
        NO_RETRY,
        "Cart Payment not accessible by caller.",
    )
    CART_PAYMENT_DATA_INVALID = ("payin_63", NO_RETRY, "Cart Payment data is invalid.")
    CART_PAYMENT_AMOUNT_INVALID = (
        "payin_64",
        NO_RETRY,
        "The provided amount is not valid.",
    )
    CART_PAYMENT_PAYMENT_METHOD_NOT_FOUND = (
        "payin_66",
        NO_RETRY,
        "Payment method used to create cart payment was not found",
    )
    CART_PAYMENT_CONCURRENT_ACCESS_ERROR = (
        "payin_67",
        SHOULD_RETRY,
        "Another process is attempting to modify the same cart payment.  Please try again later.",
    )
    CART_PAYMENT_IDEMPOTENCY_KEY_ERROR = (
        "payin_68",
        NO_RETRY,
        "The idempotency key is invalid.",
    )
    CART_PAYMENT_PAYER_NOT_FOUND_ERROR = (
        "payin_70",
        NO_RETRY,
        "No corresponding payer found for given payer_reference_id.",
    )
    CART_PAYMENT_UPDATE_DB_ERROR = (
        "payin_69",
        SHOULD_RETRY,
        "Data I/O error. Please retry again!",
    )
    PAYER_CREATE_INVALID_DATA = (
        "payin_1",
        NO_RETRY,
        "Invalid data types. Please verify your input again!",
    )
    PAYER_CREATE_STRIPE_ERROR = (
        "payin_2",
        NO_RETRY,
        "Error returned from Payment Provider.",
    )
    PAYER_CREATE_PAYER_ALREADY_EXIST = "payin_3", NO_RETRY, "Payer already exists."
    PAYER_READ_INVALID_DATA = (
        "payin_4",
        NO_RETRY,
        "Invalid data types. Please verify your input again!",
    )
    PAYER_READ_NOT_FOUND = (
        "payin_5",
        NO_RETRY,
        "Payer not found. Please ensure your payer_id is correct",
    )
    PAYER_READ_DB_ERROR = "payin_6", SHOULD_RETRY, "Data I/O error. Please retry again!"
    PAYER_UPDATE_NOT_FOUND = (
        "payin_7",
        NO_RETRY,
        "Payer not found. Please ensure your payer_id is correct",
    )
    PAYER_UPDATE_DB_ERROR_INVALID_DATA = (
        "payin_8",
        NO_RETRY,
        "Invalid data types. Please verify your input again!",
    )
    PAYER_UPDATE_INVALID_PAYER_TYPE = "payin_9", NO_RETRY, "Invalid payer type"
    PAYER_UPDATE_STRIPE_ERROR = (
        "payin_10",
        NO_RETRY,
        "Error returned from Payment Provider.",
    )
    PAYER_UPDATE_DB_ERROR = (
        "payin_11",
        SHOULD_RETRY,
        "Data I/O error. Please retry again!",
    )
    PAYER_READ_STRIPE_ERROR = (
        "payin_12",
        NO_RETRY,
        "Error returned from Payment Provider.",
    )
    PAYER_READ_STRIPE_ERROR_NOT_FOUND = "payin_13", NO_RETRY, "No such customer"
    DELETE_PAYER_REQUEST_INSERT_DB_ERROR = (
        "payin_14",
        SHOULD_RETRY,
        "Data I/O error. Please retry again!",
    )
    DELETE_PAYER_REQUEST_UPDATE_DB_ERROR = (
        "payin_15",
        SHOULD_RETRY,
        "Data I/O error. Please retry again!",
    )
    PAYER_DELETE_STRIPE_ERROR_NOT_FOUND = ("payin_16", NO_RETRY, "No such customer")
    PAYER_DELETE_STRIPE_ERROR = (
        "payin_17",
        NO_RETRY,
        "Error returned from Payment Provider.",
    )
    PAYMENT_METHOD_NO_STRIPE_CARD_FOUND = (
        "payin_30",
        NO_RETRY,
        "No Stripe Card associated to the payment method",
    )
    LIST_PAYMENT_METHOD_SORTING_METHOD_NOT_SUPPORTED = (
        "payin_31",
        NO_RETRY,
        "Sorting method not supported for list payment methods",
    )
    PAYMENT_INTENT_CREATE_STRIPE_ERROR = (
        "payin_40",
        NO_RETRY,
        "Error returned from Payment Provider. Please make sure your payer_id, payment_method_id are correct!",
    )
    PAYMENT_INTENT_CAPTURE_STRIPE_ERROR = (
        "payin_41",
        NO_RETRY,
        "Error returned from Payment Provider. Please verify parameters of capture.",
    )
    PAYMENT_INTENT_ADJUST_REFUND_ERROR = (
        "payin_42",
        NO_RETRY,
        "Cannot refund previous charge for amount increase.",
    )
    PAYMENT_INTENT_CREATE_CARD_DECLINED_ERROR = (
        "payin_43",
        NO_RETRY,
        "Cannot create payment.  Payment card declined.",
    )
    PAYMENT_INTENT_CREATE_CARD_EXPIRED_ERROR = (
        "payin_44",
        NO_RETRY,
        "Cannot create payment.  Payment card expired.",
    )
    PAYMENT_INTENT_CREATE_CARD_PROCESSING_ERROR = (
        "payin_45",
        NO_RETRY,
        "Cannot create payment.  Payment card cannot be processed.",
    )
    PAYMENT_INTENT_CREATE_CARD_INCORRECT_NUMBER_ERROR = (
        "payin_46",
        NO_RETRY,
        "Cannot create payment.  Payment card number incorrect.",
    )
    PAYMENT_INTENT_CREATE_ERROR = (
        "payin_47",
        SHOULD_RETRY,
        "An error occurred attempting your payment request.  Please try again later.",
    )
    PAYMENT_INTENT_CREATE_INVALID_SPLIT_PAYMENT_ACCOUNT = (
        "payin_48",
        NO_RETRY,
        "Invalid split payment payout account.  This is account is not configured correctly for payment use.",
    )
    PAYMENT_INTENT_CREATE_CARD_INCORRECT_CVC_ERROR = (
        "payin_49",
        NO_RETRY,
        "Cannot create payment.  Payment card cvc incorrect.",
    )
    PAYMENT_INTENT_CREATE_FAILED_ERROR = (
        "payin_50",
        SHOULD_RETRY,
        "Cannot create payment.  Payment creation failed.",
    )
    PAYMENT_INTENT_CREATE_CROSS_COUNTRY_PAYMENT_METHOD_ERROR = (
        "payin_51",
        NO_RETRY,
        "Unable to establish payment method for cross country payment.",
    )
    PAYMENT_INTENT_CREATE_INVALID_PROVIDER_PAYMENT_METHOD = (
        "payin_52",
        NO_RETRY,
        "Unable to create payment due to invalid provider payment method data.",
    )
    PAYMENT_METHOD_CREATE_INVALID_DATA = (
        "payin_20",
        NO_RETRY,
        "Invalid data types. Please verify your input again!",
    )
    PAYMENT_METHOD_CREATE_DB_ERROR = (
        "payin_21",
        SHOULD_RETRY,
        "Data I/O error. Please retry again!",
    )
    PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE = (
        "payin_22",
        NO_RETRY,
        "Invalid input payment method type!",
    )
    PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH = (
        "payin_23",
        NO_RETRY,
        "payer_id and payment_method_id mismatch! Please ensure payer owns the payment_method!!",
    )
    PAYMENT_METHOD_GET_NOT_FOUND = (
        "payin_24",
        NO_RETRY,
        "Payment method not found. Please ensure your payment_method_id is correct",
    )
    PAYMENT_METHOD_GET_INVALID_PAYER_REFERENCE_ID = (
        "invalid_payer_reference_id",
        NO_RETRY,
        "Invalid input of payer_id and payer_reference_id",
    )
    PAYMENT_METHOD_GET_DB_ERROR = (
        "payin_25",
        SHOULD_RETRY,
        "Data I/O error. Please retry again!",
    )
    PAYMENT_METHOD_CREATE_STRIPE_ERROR = (
        "payin_26",
        NO_RETRY,
        "Error returned from Payment Provider. Please make sure your token is correct!",
    )
    PAYMENT_METHOD_CREATE_INVALID_INPUT = (
        "payin_27",
        NO_RETRY,
        "Invalid input. Please ensure valid id is provided!",
    )
    PAYMENT_METHOD_DELETE_STRIPE_ERROR = (
        "payin_28",
        NO_RETRY,
        "Error returned from Payment Provider. Please make sure your payment_method_id is correct!",
    )
    PAYMENT_METHOD_DELETE_DB_ERROR = (
        "payin_29",
        SHOULD_RETRY,
        "Data I/O error. Please retry again!",
    )
    PAYMENT_METHOD_UPDATE_DB_ERROR = (
        "payin_33",
        SHOULD_RETRY,
        "Data I/O error. Please retry again!",
    )
    PAYMENT_METHOD_PAYER_CORRELATION_ID_MISMATCH = (
        "payin_34",
        NO_RETRY,
        "Mismatch in correlation ids for payer",
    )
    DISPUTE_NOT_FOUND = (
        "payin_100",
        NO_RETRY,
        "Dispute not found. Please ensure your dispute_id is correct",
    )
    DISPUTE_READ_DB_ERROR = "payin_101", NO_RETRY, "Data I/O error. Please retry again!"
    DISPUTE_READ_INVALID_DATA = (
        "payin_102",
        NO_RETRY,
        "Invalid data types. Please verify your input again!",
    )
    DISPUTE_LIST_NO_PARAMETERS = (
        "payin_103",
        NO_RETRY,
        "No parameters provides. Provide verify your input",
    )
    DISPUTE_NO_PAYER_FOR_PAYER_ID = (
        "payin_104",
        NO_RETRY,
        "The given payer_id does not have a payer associated to it",
    )
    DISPUTE_NO_STRIPE_CARD_FOR_PAYMENT_METHOD_ID = (
        "payin_105",
        NO_RETRY,
        "The given payment_method_id does not have a payment_method associated to it",
    )
    DISPUTE_LIST_NO_ID_PARAMETERS = (
        "payin_106",
        NO_RETRY,
        "No id parameters provides. Please verify your input",
    )
    DISPUTE_LIST_MORE_THAN_ID_ONE_PARAMETER = (
        "payin_107",
        NO_RETRY,
        "More than 1 id parameter provided. Please verify your input",
    )
    DISPUTE_UPDATE_STRIPE_ERROR = (
        "payin_108",
        NO_RETRY,
        "Error returned from Payment Provider.",
    )
    DISPUTE_NO_STRIPE_CARD_FOR_STRIPE_ID = (
        "payin_109",
        NO_RETRY,
        "The given dispute_id does not have a stripe_card associated to it",
    )
    DISPUTE_NO_CONSUMER_CHARGE_FOR_STRIPE_DISPUTE = (
        "payin_110",
        NO_RETRY,
        "The given dispute_id does not have a consumer_charge associated to it's stripe charge",
    )
    DISPUTE_UPDATE_DB_ERROR = (
        "payin_111",
        SHOULD_RETRY,
        "Error. Empty data returned from DB after update",
    )
    COMMANDO_DISABLED_ENDPOINT = (
        "payin_800",
        NO_RETRY,
        "API not accessible/usable in commando mode",
    )
    PAYMENT_METHOD_LIST_INVALID_PAYER_TYPE = (
        "payin_32",
        NO_RETRY,
        "Invalid payer type for list payment method",
    )
    LEGACY_STRIPE_CHARGE_UPDATE_DB_ERROR = (
        "payin_120",
        SHOULD_RETRY,
        "Data I/O error. Please retry again!",
    )
    API_NOT_IMPLEMENTED_ERROR = (
        "not_implemented",
        NO_RETRY,
        "This API is not implemented!",
    )

    def __new__(
        cls,
        value: str,
        retryable: Optional[bool] = None,  # make optional for typing check
        message: Optional[str] = None,  # make optional for typing check
    ):
        """
        Override __new__ function for StrEnum here to provide additional handles of error code attribute
        But still maintain the StrEnum behavior
        Args:
            value: enum value of the error code
            retryable: whether client can retry when seeing this error code
            message: descriptive message of this error code

        """
        obj = str.__new__(cls, value)  # type: ignore
        obj._value_ = value
        obj._message = validation.not_none(message)
        obj._retryable = validation.not_none(retryable)
        # Update class level docstring per each enum item's message
        cls.__doc__ = (
            f"{cls.__doc__}\n\n[{obj.value}]: (retryable={obj.retryable}) {obj.message}"
        )
        return obj

    @property
    def message(self) -> str:
        """
        Descriptive message for each error code.
        Whenever new error code added, need to add corresponding entry in the message map.
        """
        return self._message

    @property
    def retryable(self) -> bool:
        return self._retryable


class PayinError(PaymentError[PayinErrorCode]):
    """
    Base exception class for payin. This is base class that can be inherited by
    each business operation layer with corresponding sub error class and
    raise to application layers.  Provides automatic supplying of error message
    based on provided code.
    """

    def __init__(self, error_code: PayinErrorCode):
        """
        Base Payin exception class.

        :param error_code: payin service predefined client-facing error codes.
        """
        super(PayinError, self).__init__(
            error_code.value, error_code.message, error_code.retryable
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


class PayerDeleteError(PayinError):
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


class PaymentMethodUpdateError(PayinError):
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
        provider_charge_id: Optional[str] = None,
        provider_error_code: Optional[str] = None,
        provider_decline_code: Optional[str] = None,
        has_provider_error_details: bool = False,
    ):
        super(CartPaymentCreateError, self).__init__(error_code=error_code)
        self.provider_error_code = provider_error_code
        self.provider_decline_code = provider_decline_code
        self.provider_charge_id = provider_charge_id
        self.has_provider_error_details = has_provider_error_details


class CartPaymentReadError(PayinError):
    pass


class CartPaymentUpdateError(PayinError):
    pass


###########################################################
# Legacy Charge and StripeCharge Errors                   #
###########################################################
class PaymentChargeRefundError(PayinError):
    pass


class LegacyStripeChargeUpdateError(PayinError):
    pass


class LegacyStripeChargeCouldNotBeUpdatedError(Exception):
    pass


class LegacyStripeChargeConcurrentAccessError(PayinError):
    pass


###########################################################
# PaymentIntent Errors                                    #
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
# StripeDispute Errors                                    #
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
