from enum import Enum
from typing import TypeVar, Generic

ErrorCodeT = TypeVar("ErrorCodeT", bound=str)


class PaymentError(Generic[ErrorCodeT], Exception):
    """
    Base class for all payment internal exceptions. This is base class that can be inherited by
    each business operation layer with corresponding sub error class and
    raise to application layers.
    """

    error_code: ErrorCodeT

    def __init__(self, error_code: ErrorCodeT, error_message: str, retryable: bool):
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


###########################################
# DataBaseError
#   - DBConnectionError
#   - DBOperationError
#     + DBOperationLockNotAvailableError
#   - DBIntegrityError
#     + DBIntegrityUniqueViolationError
#   - DBProgrammingError
#   - DBDataError
#   - DBInternalError
#   - DBNotSupportedError
###########################################
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


class DatabaseError(PaymentError[DatabaseErrorCode]):
    def __init__(
        self, error_code: DatabaseErrorCode, error_message: str, retryable: bool
    ):
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


####################################
# PGPError
#   - PGPConnectionError
#   - PGPApiError
#   - PGPRateLimitError
#   - PGPAuthenticationError
#   - PGPAuthorizationError
#   - PGPIdempotencyError
#   - PGPInvalidRequestError
#   - PGPResourceNotFoundError
####################################
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


class PGPError(PaymentError[PGPErrorCode]):
    """PGP general errors.

    This is the base class for all PGP related errors.
    """

    def __init__(self, error_code: PGPErrorCode, error_message: str, retryable: bool):
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


####################################
# PaymentLockError
#   - PaymentLockAcquireError
#   - PaymentLockReleaseError
####################################
class PaymentLockErrorCode(str, Enum):
    LOCK_ACQUIRE_ERROR = "lock_acquire_error"
    LOCK_RELEASE_ERROR = "lock_release_error"


payment_lock_error_message_maps = {
    PaymentLockErrorCode.LOCK_ACQUIRE_ERROR: "unable to acquire a lock",
    PaymentLockErrorCode.LOCK_RELEASE_ERROR: "unable to release the lock",
}


class PaymentLockError(PaymentError[PaymentLockErrorCode]):
    """Payment Lock Base Error."""

    def __init__(
        self, error_code: PaymentLockErrorCode, error_message: str, retryable: bool
    ):
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


####################################
# Marqeta Related Errors
#   - MarqetaResourceAlreadyCreatedError
#   - MarqetaResourceNotFoundError
#   - MarqetaCreateUserError
#   - MarqetaCannotAssignCardError
#   - MarqetaCannotMoveCardToNewCardHolderError
#   - MarqetaCannotActivateCardError
#   - MarqetaCannotInactivateCardError
#   - MarqetaNoActiveCardOwnershipError
#   - MarqetaCardNotFoundError
####################################
class MarqetaErrorCode(str, Enum):
    MARQETA_RESOURCE_ALREADY_CREATED_ERROR = "marqeta_resource_already_created_error"
    MARQETA_RESOURCE_NOT_FOUND_ERROR = "marqeta_resource_not_found_error"
    MARQETA_CREATE_USER_ERROR = "create_marqeta_user_error"
    MARQETA_CANNOT_ASSIGN_CARD_ERROR = "cannot_assign_marqeta_card_error"
    MARQETA_CANNOT_MOVE_CARD_TO_NEW_CARDHOLDER_ERROR = (
        "cannot_move_marqeta_card_to_new_cardholder_error"
    )
    MARQETA_FAILED_TO_ACTIVATE_CARD_ERROR = "cannot_activate_marqeta_card_error"
    MARQETA_FAILED_TO_INACTIVATE_CARD_ERROR = "cannot_inactivate_marqeta_card_error"
    MARQETA_NO_ACTIVE_CARD_OWNERSHIP_DASHER_ERROR = (
        "no_active_marqeta_card_ownership_error"
    )
    MARQETA_NO_CARD_FOUND_FOR_TOKEN_ERROR = "no_card_found_for_token_error"


marqeta_error_message_maps = {
    MarqetaErrorCode.MARQETA_RESOURCE_ALREADY_CREATED_ERROR: "Marqeta resource already created.",
    MarqetaErrorCode.MARQETA_RESOURCE_NOT_FOUND_ERROR: "Marqeta resource not found.",
    MarqetaErrorCode.MARQETA_CREATE_USER_ERROR: "Error creating Marqeta user.",
    MarqetaErrorCode.MARQETA_CANNOT_ASSIGN_CARD_ERROR: "Marqeta card cannot be assigned.",
    MarqetaErrorCode.MARQETA_CANNOT_MOVE_CARD_TO_NEW_CARDHOLDER_ERROR: "Marqeta card cannot be moved to a new cardholder.",
    MarqetaErrorCode.MARQETA_FAILED_TO_ACTIVATE_CARD_ERROR: "Failed to activate marqeta card.",
    MarqetaErrorCode.MARQETA_FAILED_TO_INACTIVATE_CARD_ERROR: "Failed to inactivate marqeta card.",
    MarqetaErrorCode.MARQETA_NO_ACTIVE_CARD_OWNERSHIP_DASHER_ERROR: "No active card ownership found for dasher id.",
    MarqetaErrorCode.MARQETA_NO_CARD_FOUND_FOR_TOKEN_ERROR: "No card found for token.",
}


class MarqetaResourceAlreadyCreatedError(PaymentError[MarqetaErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_RESOURCE_ALREADY_CREATED_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_RESOURCE_ALREADY_CREATED_ERROR
            ],
            retryable=False,
        )


class MarqetaResourceNotFoundError(PaymentError[MarqetaErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_RESOURCE_NOT_FOUND_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_RESOURCE_NOT_FOUND_ERROR
            ],
            retryable=False,
        )


class MarqetaCreateUserError(PaymentError[MarqetaErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_CREATE_USER_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_CREATE_USER_ERROR
            ],
            retryable=False,
        )


class MarqetaCannotAssignCardError(PaymentError[MarqetaErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_CANNOT_ASSIGN_CARD_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_CANNOT_ASSIGN_CARD_ERROR
            ],
            retryable=False,
        )


class MarqetaCannotMoveCardToNewCardHolderError(PaymentError[MarqetaErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_CANNOT_MOVE_CARD_TO_NEW_CARDHOLDER_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_CANNOT_MOVE_CARD_TO_NEW_CARDHOLDER_ERROR
            ],
            retryable=False,
        )


class MarqetaCannotActivateCardError(PaymentError[MarqetaErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_FAILED_TO_ACTIVATE_CARD_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_FAILED_TO_ACTIVATE_CARD_ERROR
            ],
            retryable=False,
        )


class MarqetaCannotInactivateCardError(PaymentError[MarqetaErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_FAILED_TO_INACTIVATE_CARD_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_FAILED_TO_INACTIVATE_CARD_ERROR
            ],
            retryable=False,
        )


class MarqetaNoActiveCardOwnershipError(PaymentError[MarqetaErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_NO_ACTIVE_CARD_OWNERSHIP_DASHER_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_NO_ACTIVE_CARD_OWNERSHIP_DASHER_ERROR
            ],
            retryable=False,
        )


class MarqetaCardNotFoundError(PaymentError[MarqetaErrorCode]):
    def __init__(self):
        super().__init__(
            error_code=MarqetaErrorCode.MARQETA_NO_CARD_FOUND_FOR_TOKEN_ERROR,
            error_message=marqeta_error_message_maps[
                MarqetaErrorCode.MARQETA_NO_CARD_FOUND_FOR_TOKEN_ERROR
            ],
            retryable=False,
        )


####################################
# PaymentCacheError
#   - PaymentCacheGetError
#   - PaymentCacheSetError
#   - PaymentCacheCheckExistenceError
#   - PaymentCacheInvalidateError
####################################
class PaymentCacheErrorCode(str, Enum):
    CACHE_GET_ERROR = "cache_get_error"
    CACHE_SET_ERROR = "cache_set_error"
    CACHE_CHECK_EXISTENCE_ERROR = "cache_check_existence_error"
    CACHE_INVALIDATE_ERROR = "cache_invalidate_error"
    INVALID_CACHE_KEY_PARAMS = "invalid_cache_key_params"


payment_cache_error_message_maps = {
    PaymentCacheErrorCode.CACHE_GET_ERROR: "unable to get cache",
    PaymentCacheErrorCode.CACHE_SET_ERROR: "unable to set cache",
    PaymentCacheErrorCode.CACHE_CHECK_EXISTENCE_ERROR: "unable to check existence of a key in cache",
    PaymentCacheErrorCode.CACHE_INVALIDATE_ERROR: "unable to invalidate cache",
    PaymentCacheErrorCode.INVALID_CACHE_KEY_PARAMS: "invalid cache key params, should be a non-empty dict",
}


class PaymentCacheError(PaymentError[PaymentCacheErrorCode]):
    """Payment Cache Base Error."""

    def __init__(
        self, error_code: PaymentCacheErrorCode, error_message: str, retryable: bool
    ):
        super().__init__(error_code, error_message, retryable)


class PaymentCacheGetError(PaymentCacheError):
    """Payment Cache Get Error.

    Raised when unable to get from cache.
    """

    def __init__(self):
        super().__init__(
            error_code=PaymentCacheErrorCode.CACHE_GET_ERROR,
            error_message=payment_cache_error_message_maps[
                PaymentCacheErrorCode.CACHE_GET_ERROR
            ],
            retryable=True,
        )


class PaymentCacheSetError(PaymentCacheError):
    """Payment Cache Set Error.

    Raised when unable to set cache.
    """

    def __init__(self):
        super().__init__(
            error_code=PaymentCacheErrorCode.CACHE_SET_ERROR,
            error_message=payment_cache_error_message_maps[
                PaymentCacheErrorCode.CACHE_SET_ERROR
            ],
            retryable=True,
        )


class PaymentCacheCheckExistenceError(PaymentCacheError):
    """Payment Cache Check Existence Error.

    Raised when unable to check the existence in cache.
    """

    def __init__(self):
        super().__init__(
            error_code=PaymentCacheErrorCode.CACHE_CHECK_EXISTENCE_ERROR,
            error_message=payment_cache_error_message_maps[
                PaymentCacheErrorCode.CACHE_CHECK_EXISTENCE_ERROR
            ],
            retryable=True,
        )


class PaymentCacheInvalidateError(PaymentCacheError):
    """Payment Cache Invalidate Error.

    Raised when unable to invalidate cache.
    """

    def __init__(self):
        super().__init__(
            error_code=PaymentCacheErrorCode.CACHE_INVALIDATE_ERROR,
            error_message=payment_cache_error_message_maps[
                PaymentCacheErrorCode.CACHE_INVALIDATE_ERROR
            ],
            retryable=True,
        )


class PaymentCacheInvalidateCacheKeyParams(PaymentCacheError):
    """Payment Cache invalid cache key params Error.

    Raised when the passed in key params are not a non-empty dict
    """

    def __init__(self):
        super().__init__(
            error_code=PaymentCacheErrorCode.INVALID_CACHE_KEY_PARAMS,
            error_message=payment_cache_error_message_maps[
                PaymentCacheErrorCode.INVALID_CACHE_KEY_PARAMS
            ],
            retryable=True,
        )
