from enum import Enum


class DatabaseErrorCode(str, Enum):
    DB_CONNECTION_ERROR = "db_connection_error"
    DB_OPERATION_ERROR = "db_operation_error"
    DB_OPERATION_LOCK_NOT_AVAILABLE_ERROR = "db_operation_lock_not_available_error"
    DB_INTEGRITY_ERROR = "db_integrity_error"
    DB_INTEGRITY_UNIQUE_VIOLATION_ERROR = "db_integrity_unique_violation_error"
    DB_PROGRAMMING_ERROR = "db_programming_error"
    DB_DATA_ERROR = "db_data_error"
    DB_INTERNAL_ERROR = "db_internal_error"
    DB_NOT_SUPPORTED_ERROR = "db_not_supported_error"


database_error_message_maps = {
    DatabaseErrorCode.DB_OPERATION_LOCK_NOT_AVAILABLE_ERROR: "lock is not available",
    DatabaseErrorCode.DB_INTEGRITY_UNIQUE_VIOLATION_ERROR: "unique violation error",
}


class PaymentLockErrorCode(str, Enum):
    LOCK_ACQUIRE_ERROR = "lock_acquire_error"
    LOCK_RELEASE_ERROR = "lock_release_error"


payment_lock_error_message_maps = {
    PaymentLockErrorCode.LOCK_ACQUIRE_ERROR: "unable to acquire a lock",
    PaymentLockErrorCode.LOCK_RELEASE_ERROR: "unable to release the lock",
}


class PGPErrorCode(str, Enum):
    PGP_CONNECTION_ERROR = "pgp_connection_error"
    PGP_API_ERROR = "pgp_api_error"
    PGP_RATE_LIMIT_ERROR = "pgp_rate_limit_error"
    PGP_AUTHENTICATION_ERROR = "pgp_authentication_error"
    PGP_AUTHORIZATION_ERROR = "pgp_authorization_error"
    PGP_IDEMPOTENCY_ERROR = "pgp_idempotency_error"
    PGP_INVALID_REQUEST_ERROR = "pgp_invalid_request_error"
    PGP_RESOURCE_NOT_FOUND_ERROR = "pgp_resource_not_found_error"


pgp_error_message_maps = {
    PGPErrorCode.PGP_CONNECTION_ERROR: "Failed to connect to PGP",
    PGPErrorCode.PGP_API_ERROR: "Error talking to PGP service.",
    PGPErrorCode.PGP_RATE_LIMIT_ERROR: "Too many requests to PGP.",
    PGPErrorCode.PGP_AUTHENTICATION_ERROR: "Authentication error while talking to PGP.",
    PGPErrorCode.PGP_AUTHORIZATION_ERROR: "Authorization error while talking to PGP.",
    PGPErrorCode.PGP_IDEMPOTENCY_ERROR: "Idempotency error while talking to PGP.",
    PGPErrorCode.PGP_RESOURCE_NOT_FOUND_ERROR: "Resource not found from PGP.",
}


class MarqetaErrorCode(str, Enum):
    MARQETA_RESOURCE_ALREADY_CREATED_ERROR = "marqeta_resource_already_created_error"
    MARQETA_CREATE_USER_ERROR = "create_marqeta_user_error"


marqeta_error_message_maps = {
    MarqetaErrorCode.MARQETA_RESOURCE_ALREADY_CREATED_ERROR: "Marqeta resource already created.",
    MarqetaErrorCode.MARQETA_CREATE_USER_ERROR: "Error creating Marqeta user.",
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


class PaymentLockError(PaymentError):
    """Payment Lock Base Error."""

    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(error_code, error_message, retryable)


class PaymentLockAcquireError(PaymentLockError):
    """Payment Lock Acquire Error.

    Raised when unable to acquire a lock using PaymentLock.
    """

    def __init__(self):
        super().__init__(
            error_code=PaymentLockErrorCode.LOCK_ACQUIRE_ERROR,
            error_message=payment_lock_error_message_maps[
                PaymentLockErrorCode.LOCK_ACQUIRE_ERROR
            ],
            retryable=True,
        )


class PaymentLockReleaseError(PaymentLockError):
    """Payment Lock Release Error.

    Raised when unable to release a lock using PaymentLock.
    """

    def __init__(self):
        super().__init__(
            error_code=PaymentLockErrorCode.LOCK_RELEASE_ERROR,
            error_message=payment_lock_error_message_maps[
                PaymentLockErrorCode.LOCK_RELEASE_ERROR
            ],
            retryable=False,
        )


class DatabaseError(PaymentError):
    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(error_code, error_message, retryable)


class DBConnectionError(DatabaseError):
    """DB Connection Error.

    Exception raised for errors that are related to the database interface rather than the database itself, e.g., failed
    to connect to db.

    """

    def __init__(self, error_message):
        super().__init__(
            error_code=DatabaseErrorCode.DB_CONNECTION_ERROR,
            error_message=error_message,
            retryable=False,
        )


class DBOperationError(DatabaseError):
    """DB Operation Error.

    Exception raised for errors that are related to the database's operation and not necessarily under the control
    of the programmer.
    """

    def __init__(self, error_message):
        super().__init__(
            error_code=DatabaseErrorCode.DB_OPERATION_ERROR,
            error_message=error_message,
            retryable=True,
        )


class DBOperationLockNotAvailableError(DBOperationError):
    """DB Operation Error specifically for lock not available error in ledger.

    Exception raised for errors that are related to the database's operation and not necessarily under the control
    of the programmer.
    """

    def __init__(self):
        super().__init__(
            error_message=database_error_message_maps[
                DatabaseErrorCode.DB_OPERATION_LOCK_NOT_AVAILABLE_ERROR
            ]
        )


class DBIntegrityError(DatabaseError):
    """DB Integrity Error.

    Exception raised when the relational integrity of the database is affected, e.g. a foreign key check fails.
    """

    def __init__(self, error_message):
        super().__init__(
            error_code=DatabaseErrorCode.DB_INTEGRITY_ERROR,
            error_message=error_message,
            retryable=False,
        )


class DBIntegrityUniqueViolationError(DBIntegrityError):
    """DB Operation Error specifically for unique violation error in ledger.

    Exception raised for errors that are related to the database's operation and not necessarily under the control
    of the programmer.
    """

    def __init__(self):
        super().__init__(
            error_message=database_error_message_maps[
                DatabaseErrorCode.DB_INTEGRITY_UNIQUE_VIOLATION_ERROR
            ]
        )


class DBProgrammingError(DatabaseError):
    """DB Programming Error.

    Exception raised for programming errors, e.g. table not found or already exists, syntax error in the SQL statement,
    wrong number of parameters specified, etc.
    """

    def __init__(self, error_message):
        super().__init__(
            error_code=DatabaseErrorCode.DB_PROGRAMMING_ERROR,
            error_message=error_message,
            retryable=False,
        )


class DBDataError(DatabaseError):
    """DB Data Error.

    Exception raised for errors that are due to problems with the processed data like division by zero, numeric
    value out of range, etc.
    """

    def __init__(self, error_message):
        super().__init__(
            error_code=DatabaseErrorCode.DB_DATA_ERROR,
            error_message=error_message,
            retryable=False,
        )


class DBInternalError(DatabaseError):
    """DB Internal Error.

    Exception raised when the database encounters an internal error, e.g. the cursor is not valid anymore.
    """

    def __init__(self, error_message):
        super().__init__(
            error_code=DatabaseErrorCode.DB_INTERNAL_ERROR,
            error_message=error_message,
            retryable=False,
        )


class DBNotSupportedError(DatabaseError):
    """DB Not Supported Error.

    Exception raised in case a method or database API was used which is not supported by the database.
    """

    def __init__(self, error_message):
        super().__init__(
            error_code=DatabaseErrorCode.DB_NOT_SUPPORTED_ERROR,
            error_message=error_message,
            retryable=False,
        )


class PGPError(PaymentError):
    """PGP general errors.

    This is the base class for all PGP related errors.
    """

    def __init__(self, error_code: str, error_message: str, retryable: bool):
        super().__init__(error_code, error_message, retryable)


class PGPConnectionError(PGPError):
    """PGP Connection Error.

    This error means failed to connect to PGP because of network problem, dns problems. Usually it is thrown from
    client side, not actually hit PGP service.
    """

    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_CONNECTION_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_CONNECTION_ERROR],
            retryable=True,
        )


class PGPApiError(PGPError):
    """PGP API Error.

    This error means there is a PGP internal error. The status code got from PGP is 500.
    """

    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_API_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_API_ERROR],
            retryable=True,
        )


class PGPRateLimitError(PGPError):
    """PGP RateLimitError Error.

    This error means PGP rate limit has been reached. Too many requests sent to PGP at the same time.
    """

    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_RATE_LIMIT_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_RATE_LIMIT_ERROR],
            retryable=True,
        )


class PGPAuthenticationError(PGPError):
    """PGP Authentication Error.

    This error means failed to authenticate with PGP. Mostly the reason is because of invalid api key.
    """

    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_AUTHENTICATION_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_AUTHENTICATION_ERROR],
            retryable=False,
        )


class PGPAuthorizationError(PGPError):
    """PGP Authorization Error.

    This error means failed to perform operations with current key/token. Mostly it's because of permission setup.
    """

    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_AUTHORIZATION_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_AUTHORIZATION_ERROR],
            retryable=False,
        )


class PGPIdempotencyError(PGPError):
    """PGP Idempotency Error.

    This error means error occurs when an idempotency key is re-used on a request that does not match the first
    request's API endpoint and parameters.
    """

    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_IDEMPOTENCY_ERROR,
            error_message=pgp_error_message_maps[PGPErrorCode.PGP_IDEMPOTENCY_ERROR],
            retryable=False,
        )


class PGPInvalidRequestError(PGPError):
    """PGP Invalid Request Error.

    This error means the request our service sends to PGP is invalid because of internal misconfiguration, such as
    key expired, url mismatched.
    """

    def __init__(self, error_message):
        # need to pass in error_message to detail the reason of invalid request
        super().__init__(
            error_code=PGPErrorCode.PGP_INVALID_REQUEST_ERROR,
            error_message=error_message,
            retryable=False,
        )


class PGPResourceNotFoundError(PGPError):
    """PGP Resource Not Found Error.

    This error means the resource we are trying to retrieve from PGP does not exist. The status code from PGP is 404.
    """

    def __init__(self):
        super().__init__(
            error_code=PGPErrorCode.PGP_RESOURCE_NOT_FOUND_ERROR,
            error_message=pgp_error_message_maps[
                PGPErrorCode.PGP_RESOURCE_NOT_FOUND_ERROR
            ],
            retryable=False,
        )


class MarqetaResourceAlreadyCreatedError(PaymentError):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_RESOURCE_ALREADY_CREATED_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_RESOURCE_ALREADY_CREATED_ERROR
            ],
            retryable=False,
        )


class MarqetaCreateUserError(PaymentError):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_CREATE_USER_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_CREATE_USER_ERROR
            ],
            retryable=False,
        )
