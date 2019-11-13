from typing import Dict

from app.commons.core.errors import PaymentError
from enum import Enum


class PayoutError(PaymentError[str]):
    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(
            error_code=error_code, error_message=error_message, retryable=retryable
        )


###########################################################
# PayoutAccount Errors
###########################################################
class PayoutAccountErrorCode(str, Enum):
    TOKEN_INVALID = "token_invalid"
    ADDRESS_INVALID = "address_invalid"
    EMAIL_INVALID = "email_invalid"
    STATE_NOT_SUPPORTED = "state_not_supported"
    TAX_ID_INVALID = "tax_id_invalid"
    PAYOUT_ACCOUNT_DB_NOT_FOUND = "payout_account_db_not_found"
    PAYOUT_ACCOUNT_PGP_NOT_FOUND = "payout_account_pgp_not_found"


payout_account_error_message_maps = {
    PayoutAccountErrorCode.TOKEN_INVALID: "Token provided is invalid.",
    PayoutAccountErrorCode.ADDRESS_INVALID: "Address provided is not valid for current country.",
    PayoutAccountErrorCode.EMAIL_INVALID: "Email provided is not valid.",
    PayoutAccountErrorCode.STATE_NOT_SUPPORTED: "State provided not supported.",
    PayoutAccountErrorCode.TAX_ID_INVALID: "Tax id provided is not valid.",
    PayoutAccountErrorCode.PAYOUT_ACCOUNT_DB_NOT_FOUND: "Can't find payout account in db.",
    PayoutAccountErrorCode.PAYOUT_ACCOUNT_PGP_NOT_FOUND: "can't find payout account in PGP.",
}


class PayoutAccountError(PayoutError):
    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(
            error_code=error_code, error_message=error_message, retryable=retryable
        )


class PayoutAccountInvalidTokenError(PayoutAccountError):
    def __init__(self):
        super().__init__(
            error_code=PayoutAccountErrorCode.TOKEN_INVALID,
            error_message=payout_account_error_message_maps[
                PayoutAccountErrorCode.TOKEN_INVALID
            ],
            retryable=False,
        )


class PayoutAccountInvalidAddressError(PayoutAccountError):
    def __init__(self):
        super().__init__(
            error_code=PayoutAccountErrorCode.ADDRESS_INVALID,
            error_message=payout_account_error_message_maps[
                PayoutAccountErrorCode.ADDRESS_INVALID
            ],
            retryable=False,
        )


class PayoutAccountInvalidEmailError(PayoutAccountError):
    def __init__(self):
        super().__init__(
            error_code=PayoutAccountErrorCode.EMAIL_INVALID,
            error_message=payout_account_error_message_maps[
                PayoutAccountErrorCode.EMAIL_INVALID
            ],
            retryable=False,
        )


class PayoutAccountStateNotSupportedError(PayoutAccountError):
    def __init__(self):
        super().__init__(
            error_code=PayoutAccountErrorCode.STATE_NOT_SUPPORTED,
            error_message=payout_account_error_message_maps[
                PayoutAccountErrorCode.STATE_NOT_SUPPORTED
            ],
            retryable=False,
        )


class PayoutAccountTaxIdInvalidError(PayoutAccountError):
    def __init__(self):
        super().__init__(
            error_code=PayoutAccountErrorCode.TAX_ID_INVALID,
            error_message=payout_account_error_message_maps[
                PayoutAccountErrorCode.TAX_ID_INVALID
            ],
            retryable=False,
        )


class PayoutAccountDBNotFoundError(PayoutAccountError):
    def __init__(self):
        super().__init__(
            error_code=PayoutAccountErrorCode.PAYOUT_ACCOUNT_DB_NOT_FOUND,
            error_message=payout_account_error_message_maps[
                PayoutAccountErrorCode.PAYOUT_ACCOUNT_DB_NOT_FOUND
            ],
            retryable=False,
        )


class PayoutAccountPGPNotFoundError(PayoutAccountError):
    def __init__(self):
        super().__init__(
            error_code=PayoutAccountErrorCode.PAYOUT_ACCOUNT_PGP_NOT_FOUND,
            error_message=payout_account_error_message_maps[
                PayoutAccountErrorCode.PAYOUT_ACCOUNT_PGP_NOT_FOUND
            ],
            retryable=False,
        )


###########################################################
# PayoutMethod Errors                                     #
###########################################################
class PayoutMethodErrorCode(str, Enum):
    TOKEN_INVALID = "token_invalid"
    BANK_ACCOUNT_NUMBER_INVALID = "bank_account_number_invalid"
    ROUTING_NUMBER_INVALID = "routing_number_invalid"
    CARD_NUMBER_INCORRECT = "card_number_incorrect"
    CARD_NUMBER_INVALID = "card_number_invalid"
    CARD_TYPE_INVALID = "card_type_invalid"
    CARD_EXP_MONTH_INVALID = "card_exp_month_invalid"
    CARD_EXP_YEAR_INVALID = "card_exp_year_invalid"
    CARD_DECLINED = "card_declined"
    EXPIRED_CARD = "expired_card"
    PAYOUT_METHOD_DB_NOT_FOUND = "payout_method_db_not_found"
    PAYOUT_METHOD_PGP_NOT_FOUND = "payout_method_pgp_not_found"


payout_method_error_message_maps = {
    PayoutMethodErrorCode.TOKEN_INVALID: "Token provided is invalid.",
    PayoutMethodErrorCode.BANK_ACCOUNT_NUMBER_INVALID: "Bank account number provided is invalid.",
    PayoutMethodErrorCode.ROUTING_NUMBER_INVALID: "Routing number provided is invalid",
    PayoutMethodErrorCode.CARD_NUMBER_INCORRECT: "Card number provided is incorrect",
    PayoutMethodErrorCode.CARD_NUMBER_INVALID: "Card number provided is invalid.",
    PayoutMethodErrorCode.CARD_TYPE_INVALID: "Card type provided is invalid",
    PayoutMethodErrorCode.CARD_EXP_MONTH_INVALID: "Card expired month provided is invalid.",
    PayoutMethodErrorCode.CARD_EXP_YEAR_INVALID: "Card expired year provided is invalid.",
    PayoutMethodErrorCode.CARD_DECLINED: "Card provided is declined.",
    PayoutMethodErrorCode.EXPIRED_CARD: "Card provided is expired.",
    PayoutMethodErrorCode.PAYOUT_METHOD_DB_NOT_FOUND: "Can't find payout method in db.",
    PayoutMethodErrorCode.PAYOUT_METHOD_PGP_NOT_FOUND: "Can't find payout method in PGP.",
}


class PayoutMethodError(PayoutError):
    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(
            error_code=error_code, error_message=error_message, retryable=retryable
        )


class PayoutMethodInvalidTokenError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.TOKEN_INVALID,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.TOKEN_INVALID
            ],
            retryable=False,
        )


class PayoutMethodBankAccountNumberInvalidError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.BANK_ACCOUNT_NUMBER_INVALID,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.BANK_ACCOUNT_NUMBER_INVALID
            ],
            retryable=False,
        )


class PayoutMethodRoutingNumberInvalidError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.ROUTING_NUMBER_INVALID,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.ROUTING_NUMBER_INVALID
            ],
            retryable=False,
        )


class PayoutMethodCardNumberIncorrectError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.CARD_NUMBER_INCORRECT,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.CARD_NUMBER_INCORRECT
            ],
            retryable=False,
        )


class PayoutMethodCardNumberInvalidError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.CARD_NUMBER_INVALID,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.CARD_NUMBER_INVALID
            ],
            retryable=False,
        )


class PayoutMethodCardTypeInvalidError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.CARD_TYPE_INVALID,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.CARD_TYPE_INVALID
            ],
            retryable=False,
        )


class PayoutMethodCardExpMonthInvalidError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.CARD_EXP_MONTH_INVALID,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.CARD_EXP_MONTH_INVALID
            ],
            retryable=False,
        )


class PayoutMethodCardExpYearInvalidError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.CARD_EXP_YEAR_INVALID,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.CARD_EXP_YEAR_INVALID
            ],
            retryable=False,
        )


class PayoutMethodCardDeclinedError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.CARD_DECLINED,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.CARD_DECLINED
            ],
            retryable=False,
        )


class PayoutMethodExpiredCardError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.EXPIRED_CARD,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.EXPIRED_CARD
            ],
            retryable=False,
        )


class PayoutMethodDBNotFoundError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.PAYOUT_METHOD_DB_NOT_FOUND,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.PAYOUT_METHOD_DB_NOT_FOUND
            ],
            retryable=False,
        )


class PayoutMethodPGPNotFoundError(PayoutMethodError):
    def __init__(self):
        super().__init__(
            error_code=PayoutMethodErrorCode.PAYOUT_METHOD_PGP_NOT_FOUND,
            error_message=payout_method_error_message_maps[
                PayoutMethodErrorCode.PAYOUT_METHOD_PGP_NOT_FOUND
            ],
            retryable=False,
        )


###########################################################
# Transfer Errors                                         #
###########################################################
class TransferErrorCode(str, Enum):
    pass


transfer_error_message_maps: Dict[str, str] = {}


class TransferError(PayoutError):
    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(
            error_code=error_code, error_message=error_message, retryable=retryable
        )


###########################################################
# InstantPayoutErrors
#   - InstantPayoutBadRequestError
###########################################################
class InstantPayoutErrorCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    PAYOUT_CARD_NOT_EXIST = "payout_card_not_exist"
    PAYOUT_ACCOUNT_NOT_EXIST = "payout_account_not_exist"
    PGP_ACCOUNT_NOT_SETUP = "pgp_account_not_setup"
    NO_DEFAULT_PAYOUT_CARD = "no_default_payout_card"
    AMOUNT_LESS_THAN_FEE = "amount_less_than_fee"
    TRANSACTIONS_NOT_ALL_PAYABLE = "transaction_not_all_payable"
    TRANSACTIONS_TRANSFER_ID_NOT_EMPTY = "transactions_transfer_id_not_empty"
    TRANSACTIONS_PAYOUT_ID_NOT_EMPTY = "transactions_payout_id_not_empty"
    AMOUNT_BALANCE_MISMATCH = "amount_balance_mismatch"
    CREATE_PAYOUT_ERROR = "create_payout_error"
    CARD_DECLINE_ERROR = "card_decline_error"
    CURRENCY_MISMATCH = "currency_mismatch"


instant_payout_error_message_maps: Dict[str, str] = {
    InstantPayoutErrorCode.PAYOUT_CARD_NOT_EXIST: "The input card does not exist.",
    InstantPayoutErrorCode.PAYOUT_ACCOUNT_NOT_EXIST: "Payout account does not exist.",
    InstantPayoutErrorCode.PGP_ACCOUNT_NOT_SETUP: "PGP account does not setup.",
    InstantPayoutErrorCode.NO_DEFAULT_PAYOUT_CARD: "There is no default payout card for this payout account.",
    InstantPayoutErrorCode.AMOUNT_LESS_THAN_FEE: "Payout amount is less than fee.",
    InstantPayoutErrorCode.TRANSACTIONS_NOT_ALL_PAYABLE: "Transactions of the payout account are not all payable.",
    InstantPayoutErrorCode.TRANSACTIONS_TRANSFER_ID_NOT_EMPTY: "Transactions can not be part of ongoing Transfer.",
    InstantPayoutErrorCode.TRANSACTIONS_PAYOUT_ID_NOT_EMPTY: "Transactions can not be part of ongoing Instant Payout.",
    InstantPayoutErrorCode.AMOUNT_BALANCE_MISMATCH: "Payout amount does not match available balance.",
    InstantPayoutErrorCode.CARD_DECLINE_ERROR: "Can not deposit instant payout due to card decline.",
    InstantPayoutErrorCode.CURRENCY_MISMATCH: "The input currency does not match PGP provider currency.",
}


class InstantPayoutError(PayoutError):
    """Base class for all instant payout related errors."""

    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(
            error_code=error_code, error_message=error_message, retryable=retryable
        )


class InstantPayoutBadRequestError(InstantPayoutError):
    """Instant Payout Bad Request Error.

    Raised when service can not process client requests.
    """

    def __init__(self, error_code: str, error_message: str):
        super().__init__(
            error_code=error_code, error_message=error_message, retryable=False
        )


class InstantPayoutCreatePayoutError(InstantPayoutError):
    """Instant Payout Create Payout Error.

    Raised when failed to create payout, fee transaction & update transaction with payout id.
    """

    def __init__(self, error_message: str):
        super().__init__(
            error_code=InstantPayoutErrorCode.CREATE_PAYOUT_ERROR,
            error_message=error_message,
            retryable=False,
        )


class InstantPayoutCardDeclineError(InstantPayoutError):
    """Instant Payout Card Declined Error.

    Raised when failed to perform instant payout because of card declined.
    """

    def __init__(self):
        super().__init__(
            error_code=InstantPayoutErrorCode.CARD_DECLINE_ERROR,
            error_message=instant_payout_error_message_maps[
                InstantPayoutErrorCode.CARD_DECLINE_ERROR
            ],
            retryable=False,
        )
