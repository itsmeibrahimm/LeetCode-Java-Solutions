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


class UnknownInternalError(PaymentError):
    pass


DEFAULT_INTERNAL_ERROR = UnknownInternalError(
    error_code="unknown_payment_internal_error",
    error_message="payment service encountered unknown internal error",
    retryable=False,
)
