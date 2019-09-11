###########################################################
# payout_account Errors                                   #
###########################################################
from enum import Enum

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
