###########################################################
# payout_account Errors                                   #
###########################################################
from enum import Enum
from typing import Optional

from app.commons.api.models import PaymentException
from app.commons.core.errors import PaymentError

payout_account_error_message_maps = {
    "account_0": "Cannot found payout_account with given id, please verify your input."
}


class PayoutAccountErrorCode(str, Enum):
    PAYOUT_ACCOUNT_NOT_FOUND = "account_0"


class PayoutAccountNotFoundError(PaymentError):
    def __init__(self):
        super().__init__(
            error_message=payout_account_error_message_maps[
                PayoutAccountErrorCode.PAYOUT_ACCOUNT_NOT_FOUND.value
            ],
            error_code=PayoutAccountErrorCode.PAYOUT_ACCOUNT_NOT_FOUND,
            retryable=False,
        )


###########################################################
#                 Payout Errors                           #
###########################################################
payout_error_message_maps = {
    "payout_0": "Cannot make stripe transfer without stripe account id.",
    "payout_1": "This should not show up.",
    "payout_2": "Cannot create a stripe managed account(SMA) transfer without SMA fully setup.",
    "payout_3": "Cannot process payment for the given country",
    "payout_4": "This should not show up.",
    "payout_5": "This should not show up.",
    "payout_6": "This should not show up.",
    "payout_7": "Already submitted stripe transfer",
    "payout_8": "This should not show up.",
    "payout_9": "Payment account has no corresponding stripe_account",
    "payout_10": "Failed to submit sma transfer due to connection error",
    "payout_11": "Failed to submit sma transfer due to other error",
    "payout_12": "All existing Stripe transfers must be failed or canceled.",
    "payout_13": "Cannot find payment_account with given id.",
}


class PayoutErrorCode(str, Enum):
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


class PayoutError(PaymentException):
    """
    Base exception class for payout submission. This is base class that can be inherited by
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
