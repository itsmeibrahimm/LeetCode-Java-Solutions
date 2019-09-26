from enum import Enum
from typing import Optional

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.commons.api.models import PaymentException

###########################################################
#                 Payout Errors                           #
###########################################################
payout_error_message_maps = {
    # payout errors
    # payout_1, payout_4, payout_5, payout_6, payout_8, payout_15 requires customized error message
    "payout_0": "Cannot make stripe transfer without stripe account id.",
    "payout_1": "",
    "payout_2": "Cannot create a stripe managed account(SMA) transfer without SMA fully setup.",
    "payout_3": "Cannot process payment for the given country.",
    "payout_4": "",
    "payout_5": "",
    "payout_6": "",
    "payout_7": "Already submitted stripe transfer",
    "payout_8": "",
    "payout_9": "Payment account has no corresponding stripe_account",
    "payout_10": "Failed to submit sma transfer due to connection error",
    "payout_11": "Failed to submit sma transfer due to other error",
    "payout_12": "All existing Stripe transfers must be failed or canceled.",
    "payout_13": "Cannot find payment_account with given id.",
    "payout_14": "Failed to submit stripe payout due to RateLimitError",
    "payout_15": "Can only cancel if status is pending",
    # payout account errors
    "account_0": "Cannot found payout_account with given id, please verify your input.",
    "account_1": "PGP account has not set up, please verify your payout account.",
    "account_2": "Create external payment gateway account failed due to invalid request error.",
    "account_3": "Create external payment gateway account failed due to some error.",
    "account_4": "Update external payment gateway account failed due to some error.",
    # payout method errors
    "payout_method_0": "Cannot find a payout method for the given payout account id.",
    "payout_method_1": "Cannot find a payout card for the given payout account id.",
    "payout_method_2": "Cannot find a default payout card for the given payout account id.",
    "payout_method_3": "Some issue happened for creating a payout method, please try again later.",
}


class PayoutErrorCode(str, Enum):
    # payout error code
    INVALID_STRIPE_ACCOUNT_ID = "payout_0"
    MISMATCHED_TRANSFER_PAYMENT_ACCOUNT = "payout_1"
    INVALID_STRIPE_MANAGED_ACCOUNT = "payout_2"
    UNSUPPORTED_COUNTRY = "payout_3"
    STRIPE_PAYOUT_ACCT_MISSING = "payout_4"
    STRIPE_PAYOUT_DISALLOWED = "payout_5"
    STRIPE_INVALID_REQUEST_ERROR = "payout_6"
    DUPLICATE_STRIPE_TRANSFER = "payout_7"
    STRIPE_SUBMISSION_ERROR = "payout_8"
    INVALID_STRIPE_ACCOUNT = "payout_9"
    API_CONNECTION_ERROR = "payout_10"
    OTHER_ERROR = "payout_11"
    TRANSFER_PROCESSING = "payout_12"
    INVALID_PAYMENT_ACCOUNT_ID = "payout_13"
    RATE_LIMIT_ERROR = "payout_14"
    INVALID_STRIPE_PAYOUT = "payout_15"

    # payout account error code
    PAYOUT_ACCOUNT_NOT_FOUND = "account_0"
    PGP_ACCOUNT_NOT_FOUND = "account_1"
    PGP_ACCOUNT_CREATE_INVALID_REQUEST = "account_2"
    PGP_ACCOUNT_CREATE_ERROR = "account_3"
    PGP_ACCOUNT_UPDATE_ERROR = "account_4"

    # payout method error code
    PAYOUT_METHOD_NOT_FOUND = "payout_method_0"
    PAYOUT_CARD_NOT_FOUND = "payout_method_1"
    DEFAULT_PAYOUT_CARD_NOT_FOUND = "payout_method_2"
    PAYOUT_METHOD_CREATE_ERROR = "payout_method_3"


class PayoutError(PaymentException):
    """
    Base exception class for payout. This is base class that can be inherited by
    each business operation layer with corresponding sub error class and
    raise to application layers.  Provides automatic supplying of error message
    based on provided code.
    """

    def __init__(
        self,
        http_status_code: int,
        error_code: PayoutErrorCode,
        retryable: bool,
        error_message: Optional[str] = None,
    ):
        """
        Base Payout exception class.

        :param http_status_code: returned http status code.
        :param error_code: predefined client-facing error codes.
        :param error_message: specific error_msg will be passed in if it formatted with params otherwise it will be None
        :param retryable: identify if the error is retryable or not.
        """
        super(PayoutError, self).__init__(
            http_status_code,
            error_code.value,
            error_message=error_message
            if error_message
            else payout_error_message_maps[error_code.value],
            retryable=retryable,
        )


###########################################################
# payout_account Errors                                   #
###########################################################
def payout_account_not_found_error() -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_message=payout_error_message_maps[
            PayoutErrorCode.PAYOUT_ACCOUNT_NOT_FOUND.value
        ],
        error_code=PayoutErrorCode.PAYOUT_ACCOUNT_NOT_FOUND,
        retryable=False,
    )


def pgp_account_not_found_error() -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_message=payout_error_message_maps[
            PayoutErrorCode.PGP_ACCOUNT_NOT_FOUND.value
        ],
        error_code=PayoutErrorCode.PGP_ACCOUNT_NOT_FOUND,
        retryable=False,
    )


def pgp_account_create_invalid_request(error_message: str = None) -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_message=error_message
        if error_message
        else payout_error_message_maps[PayoutErrorCode.PGP_ACCOUNT_NOT_FOUND.value],
        error_code=PayoutErrorCode.PGP_ACCOUNT_NOT_FOUND,
        retryable=False,
    )


def pgp_account_create_error(error_message: str = None) -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        error_message=error_message
        if error_message
        else payout_error_message_maps[PayoutErrorCode.PGP_ACCOUNT_CREATE_ERROR.value],
        error_code=PayoutErrorCode.PGP_ACCOUNT_CREATE_ERROR,
        retryable=False,
    )


def pgp_account_update_error(error_message: str = None) -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        error_message=error_message
        if error_message
        else payout_error_message_maps[PayoutErrorCode.PGP_ACCOUNT_UPDATE_ERROR.value],
        error_code=PayoutErrorCode.PGP_ACCOUNT_UPDATE_ERROR,
        retryable=False,
    )


###########################################################
# payout_method Errors                                    #
###########################################################
def payout_method_not_found_error() -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_404_NOT_FOUND,
        error_message=payout_error_message_maps[
            PayoutErrorCode.PAYOUT_METHOD_NOT_FOUND.value
        ],
        error_code=PayoutErrorCode.PAYOUT_METHOD_NOT_FOUND,
        retryable=False,
    )


def payout_card_not_found_error() -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_404_NOT_FOUND,
        error_message=payout_error_message_maps[
            PayoutErrorCode.PAYOUT_CARD_NOT_FOUND.value
        ],
        error_code=PayoutErrorCode.PAYOUT_CARD_NOT_FOUND,
        retryable=False,
    )


def default_payout_card_not_found_error() -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_404_NOT_FOUND,
        error_message=payout_error_message_maps[
            PayoutErrorCode.DEFAULT_PAYOUT_CARD_NOT_FOUND.value
        ],
        error_code=PayoutErrorCode.DEFAULT_PAYOUT_CARD_NOT_FOUND,
        retryable=False,
    )


def payout_method_create_error() -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        error_message=payout_error_message_maps[
            PayoutErrorCode.PAYOUT_METHOD_CREATE_ERROR.value
        ],
        error_code=PayoutErrorCode.PAYOUT_METHOD_CREATE_ERROR,
        retryable=False,
    )
