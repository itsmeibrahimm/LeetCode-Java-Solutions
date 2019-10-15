from enum import Enum


class DatabaseErrorCode(str, Enum):
    DB_CONNECTION_ERROR = "db_connection_error"
    DB_OPERATION_ERROR = "db_operation_error"
    DB_INTEGRITY_ERROR = "db_integrity_error"
    DB_PROGRAMMING_ERROR = "db_programming_error"


db_error_message_maps = {
    DatabaseErrorCode.DB_CONNECTION_ERROR: "Failed to connect to db.",
    DatabaseErrorCode.DB_OPERATION_ERROR: "Cancel statement due to timeout.",
    DatabaseErrorCode.DB_INTEGRITY_ERROR: "Db integrity error.",
    DatabaseErrorCode.DB_PROGRAMMING_ERROR: "SQL error.",
}


class PGPErrorCode(str, Enum):
    PGP_CONNECTION_ERROR = "pgp_connection_error"
    PGP_API_ERROR = "pgp_api_error"
    PGP_RATE_LIMIT_ERROR = "pgp_rate_limit_error"
    PGP_AUTHENTICATION_ERROR = "pgp_authentication_error"
    PGP_AUTHORIZATION_ERROR = "pgp_authorization_error"
    PGP_IDEMPOTENCY_ERROR = "pgp_idempotency_error"
    PGP_INVALID_REQUEST_ERROR = "pgp_invalid_request_error"


pgp_error_message_maps = {
    PGPErrorCode.PGP_CONNECTION_ERROR: "Failed to connect to PGP",
    PGPErrorCode.PGP_API_ERROR: "Error talking to PGP service.",
    PGPErrorCode.PGP_RATE_LIMIT_ERROR: "Too many requests to PGP.",
    PGPErrorCode.PGP_AUTHENTICATION_ERROR: "Authentication error while talking to PGP.",
    PGPErrorCode.PGP_AUTHORIZATION_ERROR: "Authorization error while talking to PGP.",
    PGPErrorCode.PGP_IDEMPOTENCY_ERROR: "Idempotency error while talking to PGP.",
}


class PaymentError(Exception):
    """
    Base class for all payment internal exceptions. This is base class that can be inherited by
    each business operation layer with corresponding sub error class and
    raise to application layers.
    """

    def __init__(self, error_code: str, error_message: str, retryable: bool):
        """
        Base exception class.

        :param error_code: payment service predefined client-facing error codes.
        :param error_message: friendly error message for client reference.
        :param retryable: identify if the error is retryable or not.
        """
        super(PaymentError, self).__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.retryable = retryable


class DatabaseError(PaymentError):
    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(error_code, error_message, retryable)


class DBConnectionError(DatabaseError):
    def __init__(self):
        super().__init__(
            error_code=DatabaseErrorCode.DB_CONNECTION_ERROR,
            error_message=db_error_message_maps[DatabaseErrorCode.DB_CONNECTION_ERROR],
            retryable=True,
        )


class DBOperationError(DatabaseError):
    def __init__(self):
        super().__init__(
            error_code=DatabaseErrorCode.DB_OPERATION_ERROR,
            error_message=db_error_message_maps[DatabaseErrorCode.DB_OPERATION_ERROR],
            retryable=True,
        )


class DBIntegrityError(DatabaseError):
    def __init__(self):
        super().__init__(
            error_code=DatabaseErrorCode.DB_INTEGRITY_ERROR,
            error_message=db_error_message_maps[DatabaseErrorCode.DB_INTEGRITY_ERROR],
            retryable=False,
        )


class DBProgrammingError(DatabaseError):
    def __init__(self):
        super().__init__(
            error_code=DatabaseErrorCode.DB_PROGRAMMING_ERROR,
            error_message=db_error_message_maps[DatabaseErrorCode.DB_PROGRAMMING_ERROR],
            retryable=False,
        )


class PGPError(PaymentError):
    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(error_code, error_message, retryable)


class PGPConnectionError(PGPError):
    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_CONNECTION_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_CONNECTION_ERROR],
            retryable=True,
        )


class PGPApiError(PGPError):
    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_API_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_API_ERROR],
            retryable=True,
        )


class PGPRateLimitError(PGPError):
    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_RATE_LIMIT_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_RATE_LIMIT_ERROR],
            retryable=True,
        )


class PGPAuthenticationError(PGPError):
    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_AUTHENTICATION_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_AUTHENTICATION_ERROR],
            retryable=False,
        )


class PGPAuthorizationError(PGPError):
    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_AUTHORIZATION_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_AUTHORIZATION_ERROR],
            retryable=False,
        )


class PGPIdempotencyError(PGPError):
    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_IDEMPOTENCY_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_IDEMPOTENCY_ERROR],
            retryable=False,
        )


class PGPInvalidRequestError(PGPError):
    def __init__(self, error_message):
        # need to pass in error_message to detail the reason of invalid request
        super().__init__(
            error_code=PGPErrorCode.PGP_INVALID_REQUEST_ERROR,
            error_message=error_message,
            retryable=False,
        )
