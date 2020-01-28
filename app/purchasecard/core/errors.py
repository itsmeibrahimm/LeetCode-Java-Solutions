from enum import Enum

from app.commons.core.errors import PaymentError


class PurchaseCardError(PaymentError[str]):
    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(
            error_code=error_code, error_message=error_message, retryable=retryable
        )


###########################################################
# Purchasecard DataModel Errors
###########################################################
class StoreMastercardDataErrorCode(str, Enum):
    STORE_MASTERCARD_DATA_NOT_FOUND_ERROR = "store_mastercard_data_not_found_error"


store_mastercard_data_error_message_maps = {
    StoreMastercardDataErrorCode.STORE_MASTERCARD_DATA_NOT_FOUND_ERROR: "Fail to update an existing store mastercard data record"
}


class StoreMastercardDataNotFoundError(PaymentError[StoreMastercardDataErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=StoreMastercardDataErrorCode.STORE_MASTERCARD_DATA_NOT_FOUND_ERROR,
            error_message=store_mastercard_data_error_message_maps[
                StoreMastercardDataErrorCode.STORE_MASTERCARD_DATA_NOT_FOUND_ERROR
            ],
            retryable=False,
        )


class MarqetaTransactionErrorCode(str, Enum):
    MARQEATA_TRANSACTION_NOT_FOUND_ERROR = "marqeta_transaction_not_found_error"


marqeta_transaction_error_message_maps = {
    MarqetaTransactionErrorCode.MARQEATA_TRANSACTION_NOT_FOUND_ERROR: "Unable to find Marqeta transaction for given input"
}


class MarqetaTransactionNotFoundError(PaymentError[MarqetaTransactionErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaTransactionErrorCode.MARQEATA_TRANSACTION_NOT_FOUND_ERROR,
            error_message=marqeta_transaction_error_message_maps[
                MarqetaTransactionErrorCode.MARQEATA_TRANSACTION_NOT_FOUND_ERROR
            ],
            retryable=False,
        )


class MarqetaTransactionEventErrorCode(str, Enum):
    MARQEATA_TRANSACTION_EVENT_NOT_FOUND_ERROR = "marqeta_transaction_not_found_error"


marqeta_transaction_event_error_message_maps = {
    MarqetaTransactionEventErrorCode.MARQEATA_TRANSACTION_EVENT_NOT_FOUND_ERROR: "Unable to find Marqeta transaction event for given input"
}


class MarqetaTransactionEventNotFoundError(
    PaymentError[MarqetaTransactionEventErrorCode]
):
    def __init__(self):
        super().__init__(
            error_code=MarqetaTransactionEventErrorCode.MARQEATA_TRANSACTION_EVENT_NOT_FOUND_ERROR,
            error_message=marqeta_transaction_event_error_message_maps[
                MarqetaTransactionEventErrorCode.MARQEATA_TRANSACTION_EVENT_NOT_FOUND_ERROR
            ],
            retryable=False,
        )


class MarqetaCardOwnershipErrorCode(str, Enum):
    CARD_OWNERSHIP_NOT_FOUND_ERROR = "card_ownership_not_found_error"


card_ownership_error_message_maps = {
    MarqetaCardOwnershipErrorCode.CARD_OWNERSHIP_NOT_FOUND_ERROR: "Unable to find card ownership for given input"
}


class MarqetaCardOwnershipNotFoundError(PaymentError[MarqetaTransactionEventErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaCardOwnershipErrorCode.CARD_OWNERSHIP_NOT_FOUND_ERROR,
            error_message=card_ownership_error_message_maps[
                MarqetaCardOwnershipErrorCode.CARD_OWNERSHIP_NOT_FOUND_ERROR
            ],
            retryable=False,
        )


###########################################################
# JITFunding Errors
###########################################################
INPUT_PARAM_INVALID_ERROR_CODE = "input_params_invalid"
INVALID_EXEMPTION_INPUT_ERROR_MESSAGE = "Cannot parse given {}"


class PurchaseCardInvalidInputError(PurchaseCardError):
    def __init__(self, id_param: str):
        super().__init__(
            error_code=INPUT_PARAM_INVALID_ERROR_CODE,
            error_message=INVALID_EXEMPTION_INPUT_ERROR_MESSAGE.format(id_param),
            retryable=False,
        )


###########################################################
# AuthProcessor Errors
###########################################################
class AuthProcessorErrorCodes(str, Enum):
    AUTH_REQUEST_NOT_FOUND_ERROR = "auth_request_not_found"
    AUTH_REQUEST_NO_STATE_ERROR = "auth_request_no_state"


auth_processor_error_message_maps = {
    AuthProcessorErrorCodes.AUTH_REQUEST_NOT_FOUND_ERROR: "Unable to find auth request for given input",
    AuthProcessorErrorCodes.AUTH_REQUEST_NO_STATE_ERROR: "There is no corresponding state for this auth request",
}


class AuthRequestNotFoundError(PurchaseCardError):
    def __init__(self):
        super().__init__(
            error_code=AuthProcessorErrorCodes.AUTH_REQUEST_NOT_FOUND_ERROR,
            error_message=auth_processor_error_message_maps[
                AuthProcessorErrorCodes.AUTH_REQUEST_NOT_FOUND_ERROR
            ],
            retryable=False,
        )


class AuthRequestInconsistentStateError(PurchaseCardError):
    def __init__(self):
        super().__init__(
            error_code=AuthProcessorErrorCodes.AUTH_REQUEST_NO_STATE_ERROR,
            error_message=auth_processor_error_message_maps[
                AuthProcessorErrorCodes.AUTH_REQUEST_NO_STATE_ERROR
            ],
            retryable=False,
        )
