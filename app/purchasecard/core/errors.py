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


###########################################################
# JITFunding Errors
###########################################################
class ExemptionErrorCode(str, Enum):
    INVALID_EXEMPTION_INPUT_ERROR = "input_params_invalid"


jit_funding_error_message_maps = {
    ExemptionErrorCode.INVALID_EXEMPTION_INPUT_ERROR: "Cannot parse given delivery id, creator id or dasher id"
}


class ExemptionCreationInvalidInputError(PurchaseCardError):
    def __init__(self):
        super().__init__(
            error_code=ExemptionErrorCode.INVALID_EXEMPTION_INPUT_ERROR,
            error_message=jit_funding_error_message_maps[
                ExemptionErrorCode.INVALID_EXEMPTION_INPUT_ERROR
            ],
            retryable=False,
        )
