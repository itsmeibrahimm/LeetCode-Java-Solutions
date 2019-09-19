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
    "payout_10": "Failed to submit sma transfer due to connection error",
    "payout_11": "Failed to submit sma transfer due to other error",
}


class PayoutErrorCode(str, Enum):
    INVALID_STRIPE_ACCOUNT_ID = "payout_0"
    MISMATCHED_TRANSFER_PAYMENT_ACCOUNT = "payout_1"
    INVALID_STRIPE_MANAGED_ACCOUNT = "payout_2"
    UNHANDLED_COUNTRY = "payout_3"
    API_CONNECTION_ERROR = "payout_10"
    OTHER_ERROR = "payout_11"


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
