from enum import Enum


class PaymentErrorCode(str, Enum):
    NOT_FOUND_ERROR = "not_found_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    INVALID_REQUEST_ERROR = "invalid_request_error"
    UNKNOWN_INTERNAL_ERROR = "unknown_payment_internal_error"


class BadRequestErrorCode(str, Enum):
    # Following 3 Error codes for InvalidRequestError
    TYPE_ERROR = "type_error"
    NOT_NULL_ERROR = "not_null_error"
    INVALID_VALUE_ERROR = "invalid_value_error"


payment_error_message_maps = {
    BadRequestErrorCode.TYPE_ERROR: "Invalid type.",
    BadRequestErrorCode.NOT_NULL_ERROR: "Field can't be null.",
    BadRequestErrorCode.INVALID_VALUE_ERROR: "Field value is invalid.",
    PaymentErrorCode.NOT_FOUND_ERROR: "Record can't be found.",
    PaymentErrorCode.RATE_LIMIT_ERROR: "Too many requests.",
    PaymentErrorCode.AUTHENTICATION_ERROR: "No valid api token provided.",
    PaymentErrorCode.AUTHORIZATION_ERROR: "Not authorized for current operation. Permission forbidden.",
    PaymentErrorCode.INVALID_REQUEST_ERROR: "The input of current request is invalid.",
    PaymentErrorCode.UNKNOWN_INTERNAL_ERROR: "payment service encountered unknown internal error",
}
