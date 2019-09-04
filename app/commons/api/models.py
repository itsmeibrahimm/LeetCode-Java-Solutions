from abc import ABC

from fastapi import HTTPException
from pydantic import BaseModel


class PaymentRequest(BaseModel, ABC):
    """
    Base pydantic request model for all payment service APIs
    """

    pass


class PaymentResponse(BaseModel, ABC):
    """
    Base pydantic response model for all payment service APIs
    """

    pass


class PaymentException(HTTPException):
    """
    Payment external exception class. This is application-level class that can be used
    by each FastAPI router to return error back to client.
    """

    def __init__(
        self,
        http_status_code: int,
        error_code: str,
        error_message: str,
        retryable: bool,
    ):
        """
        External exception class.

        :param http_status_code: http status code
        :param error_code: payin service predefined client-facing error codes.
        :param error_message: friendly error message for client reference.
        :param retryable: identify if the error is retryable or not.
        """
        super().__init__(status_code=http_status_code, detail=error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.retryable = retryable


class PaymentErrorResponseBody(BaseModel):
    """
    Customized payment error http response body.

    :param error_code: payin service predefined client-facing error codes.
    :param error_message: friendly error message for client reference.
    :param retryable: identify if the error is retryable or not.
    """

    error_code: str
    error_message: str
    retryable: bool
