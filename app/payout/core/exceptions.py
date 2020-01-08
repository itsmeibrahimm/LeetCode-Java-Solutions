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
    # payout_1, payout_4, payout_5, payout_6, payout_8, payout_15, payout_16 requires customized error message
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
    "payout_11": "Failed to submit sma transfer due to other error",
    "payout_12": "All existing Stripe transfers must be failed or canceled.",
    "payout_13": "Cannot find payment_account with given id.",
    "payout_15": "Can only cancel if status is pending",
    "payout_16": "",
    "payout_17": "Amount does not match transaction amount.",
    "payout_18": "Transfer is in invalid state",
    "payout_19": "Transfer already deleted.",
    "payout_20": "Duplicate transfer.",
    "payout_21": "Transfers are disabled for this account",
    "payout_22": "Cannot find corresponding transfer with given transfer id",
    "payout_23": "transfer_permission_error",
    "payout_24": "Transfer amount exceeds limit.",
    "payout_25": "Cannot make a negative transfer.",
    "payout_26": "Invalid input, please validate.",
    "payout_27": "Unsupported use case, please validate input parameters.",
    "payout_28": "Payout country does not match",
    "payout_29": "Payment for the account is blocked",
    "payout_30": "No corresponding transactions found",
    "payout_31": "Given payout day and account payout day not match",
    # payout account errors
    "account_0": "Cannot found payout_account with given id, please verify your input.",
    "account_1": "PGP account has not set up, please verify your payout account.",
    "account_2": "Create external payment gateway account failed due to invalid request error.",
    "account_3": "Create external payment gateway account failed due to some error.",
    "account_4": "Update external payment gateway account failed due to some error.",
    "account_5": "No entity found on payment account, skip",
    # payout method errors
    "payout_method_0": "Cannot find a payout method with the given payout account id.",
    "payout_method_1": "Cannot find a payout card for the given payout account id.",
    "payout_method_2": "Cannot find a default payout card for the given payout account id.",
    "payout_method_3": "Some issue happened for creating a payout method, please try again later.",
    "payout_method_4": "Cannot find a payout method with the given id.",
    "payout_method_5": "Cannot find a payout card with the given id.",
    "payout_method_6": "The payout_account id for the payout_method is not matching with the one is given.",
    "payout_method_7": "The payout_method update failed due to some error.",
    # transaction errors
    "transaction_1": "The transaction is not valid for reverse",
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
    OTHER_ERROR = "payout_11"
    TRANSFER_PROCESSING = "payout_12"
    INVALID_PAYMENT_ACCOUNT_ID = "payout_13"
    INVALID_STRIPE_PAYOUT = "payout_15"
    DUMMY_TRANSFER_CREATION_FAILED = "payout_16"
    MISMATCHED_TRANSFER_AMOUNT = "payout_17"
    TRANSFER_INVALID_STATE = "payout_18"
    TRANSFER_ALREADY_DELETED = "payout_19"
    DUPLICATE_TRANSFER = "payout_20"
    TRANSFER_DISABLED_ERROR = "payout_21"
    TRANSFER_NOT_FOUND = "payout_22"
    TRANSFER_PERMISSION_ERROR = "payout_23"
    TRANSFER_AMOUNT_OVER_LIMIT = "payout_24"
    TRANSFER_AMOUNT_NEGATIVE = "payout_25"
    INVALID_INPUT = "payout_26"
    UNSUPPORTED_USECASE = "payout_27"
    PAYOUT_COUNTRY_NOT_MATCH = "payout_28"
    PAYMENT_BLOCKED = "payout_29"
    NO_UNPAID_TRANSACTION_FOUND = "payout_30"
    PAYOUT_DAY_NOT_MATCH = "payout_31"

    # payout account error code
    PAYOUT_ACCOUNT_NOT_FOUND = "account_0"
    PGP_ACCOUNT_NOT_FOUND = "account_1"
    PGP_ACCOUNT_CREATE_INVALID_REQUEST = "account_2"
    PGP_ACCOUNT_CREATE_ERROR = "account_3"
    PGP_ACCOUNT_UPDATE_ERROR = "account_4"
    PAYMENT_ACCOUNT_ENTITY_NOT_FOUND = "account_5"

    # payout method error code
    PAYOUT_METHOD_NOT_FOUND_FOR_ACCOUNT = "payout_method_0"
    PAYOUT_CARD_NOT_FOUND_FOR_ACCOUNT = "payout_method_1"
    DEFAULT_PAYOUT_CARD_NOT_FOUND = "payout_method_2"
    PAYOUT_METHOD_CREATE_ERROR = "payout_method_3"
    PAYOUT_METHOD_NOT_FOUND = "payout_method_4"
    PAYOUT_CARD_NOT_FOUND = "payout_method_5"
    PAYOUT_ACCOUNT_NOT_MATCH = "payout_method_6"
    PAYOUT_METHOD_UPDATE_FAILED = "payout_method_7"

    # transaction error code
    TRANSACTION_BAD_QUERY_PARAMETER = "transaction_0"
    TRANSACTION_INVALID = "transaction_1"


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
        else payout_error_message_maps[
            PayoutErrorCode.PGP_ACCOUNT_CREATE_INVALID_REQUEST.value
        ],
        error_code=PayoutErrorCode.PGP_ACCOUNT_CREATE_INVALID_REQUEST,
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
def payout_method_not_found_for_account_error() -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_404_NOT_FOUND,
        error_message=payout_error_message_maps[
            PayoutErrorCode.PAYOUT_METHOD_NOT_FOUND_FOR_ACCOUNT.value
        ],
        error_code=PayoutErrorCode.PAYOUT_METHOD_NOT_FOUND_FOR_ACCOUNT,
        retryable=False,
    )


def payout_card_not_found_for_account_error() -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_404_NOT_FOUND,
        error_message=payout_error_message_maps[
            PayoutErrorCode.PAYOUT_CARD_NOT_FOUND_FOR_ACCOUNT.value
        ],
        error_code=PayoutErrorCode.PAYOUT_CARD_NOT_FOUND_FOR_ACCOUNT,
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


def payout_account_not_match_error() -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_message=payout_error_message_maps[
            PayoutErrorCode.PAYOUT_ACCOUNT_NOT_MATCH.value
        ],
        error_code=PayoutErrorCode.PAYOUT_ACCOUNT_NOT_MATCH,
        retryable=False,
    )


def payout_method_update_error(error_message: str) -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        error_message=error_message
        if error_message
        else payout_error_message_maps[
            PayoutErrorCode.PAYOUT_METHOD_UPDATE_FAILED.value
        ],
        error_code=PayoutErrorCode.PAYOUT_METHOD_UPDATE_FAILED,
        retryable=False,
    )


###########################################################
# transactions Errors                                     #
###########################################################
def transaction_bad_query_parameters(error_message: str) -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_message=error_message,
        error_code=PayoutErrorCode.TRANSACTION_BAD_QUERY_PARAMETER,
        retryable=False,
    )


def transaction_invalid(error_message: str) -> PayoutError:
    return PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_message=error_message
        if error_message
        else payout_error_message_maps[PayoutErrorCode.TRANSACTION_INVALID.value],
        error_code=PayoutErrorCode.TRANSACTION_INVALID,
        retryable=False,
    )
