from enum import Enum

from app.commons.error.errors import PaymentError

# mx_ledger related error will use ledger_1~ledger_9
# mx_scheduled_ledger related error will use ledger_10~ledger_19
# mx_txn related error will use ledger_20~ledger_29
ledger_error_message_maps = {
    "ledger_0": "Error encountered while inserting mx_ledger and creating mx_txn, please verify your input.",
    "ledger_1": "Cannot found mx_ledger with given id, please verify your input.",
    "ledger_2": "Cannot insert mx_ledger due to unique constraint violation, please verify your input.",
    "ledger_3": "Cannot update mx_ledger due to lock not available error.",
    "ledger_4": "Cannot process mx_ledger to PROCESSING",
    "ledger_5": "State of mx_ledger cannot be processed to PROCESSING",
    "ledger_6": "Error encountered while processing negative balance mx_ledger",
    "ledger_7": "OperationalError encountered while processing mx_ledger.",
    "ledger_8": "Cannot submit mx_ledger",
    "ledger_9": "Cannot insert mx_ledger due to integrity error.",
    "ledger_10": "Cannot found mx_scheduled_ledger with given id, please verify your input.",
    "ledger_20": "Error encountered while inserting mx_txn, please verify your input.",
    "ledger_21": "OperationalError encountered while inserting mx_txn.",
}


class LedgerErrorCode(str, Enum):
    MX_LEDGER_CREATE_ERROR = "ledger_0"
    MX_LEDGER_NOT_FOUND = "ledger_1"
    MX_LEDGER_CREATE_UNIQUE_VIOLATION_ERROR = "ledger_2"
    MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR = "ledger_3"
    MX_LEDGER_PROCESS_ERROR = "ledger_4"
    MX_LEDGER_INVALID_PROCESS_STATE = "ledger_5"
    MX_LEDGER_ROLLOVER_ERROR = "ledger_6"
    MX_LEDGER_OPERATIONAL_ERROR = "ledger_7"
    MX_LEDGER_SUBMIT_ERROR = "ledger_8"
    MX_LEDGER_CREATE_INTEGRITY_ERROR = "ledger_9"
    MX_SCHEDULED_LEDGER_NOT_FOUND = "ledger_10"
    MX_TXN_CREATE_ERROR = "ledger_20"
    MX_TXN_OPERATIONAL_ERROR = "ledger_21"


class LedgerError(PaymentError):
    """
    Base exception class for ledger. This is base class that can be inherited by
    each business operation layer with corresponding sub error class and
    raise to application layers.  Provides automatic supplying of error message
    based on provided code.
    """

    def __init__(self, error_code: LedgerErrorCode, retryable: bool):
        """
        Base Ledger exception class.

        :param error_code: ledger service predefined client-facing error codes.
        :param retryable: identify if the error is retryable or not.
        """
        super(LedgerError, self).__init__(
            error_code.value, ledger_error_message_maps[error_code.value], retryable
        )


###########################################################
# mx_ledger Errors                                        #
###########################################################
class MxLedgerCreationError(PaymentError):
    pass


class MxLedgerProcessError(PaymentError):
    pass


class MxLedgerInvalidProcessStateError(PaymentError):
    pass


class MxLedgerReadError(PaymentError):
    pass


class MxLedgerLockError(PaymentError):
    pass


class MxLedgerSubmissionError(PaymentError):
    pass


class MxLedgerCreateUniqueViolationError(PaymentError):
    pass


###########################################################
# mx_transaction Errors                                   #
###########################################################
class MxTransactionCreationError(PaymentError):
    pass
