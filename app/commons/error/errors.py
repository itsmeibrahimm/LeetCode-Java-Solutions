from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from starlette.responses import JSONResponse


class PaymentError(Exception):
    """
    Base exception class. This is base class that can be inherited by
    each business operation layer with corresponding sub error class and
    raise to application layers.
    """

    def __init__(self, error_code: str, error_message: str, retryable: bool):
        """
        Base exception class.

        :param error_code: payin service predefined client-facing error codes.
        :param error_message: friendly error message for client reference.
        :param retryable: identify if the error is retryable or not.
        """
        super(PaymentError, self).__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.retryable = retryable


class PaymentException(Exception):
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
        # super(PaymentException, self).__init__(error_message)
        self.http_status_code = http_status_code
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


def create_payment_error_response_blob(
    status_code: int, resp_blob: PaymentErrorResponseBody
):
    """
    Create customized payment error http response.

    :param status_code: http status code.
    :param resp_blob: PaymentErrorResponseBody object.
    :return:
    """
    # FIXME: this method should be replaced by FASTAPI custom exception handler:
    #        https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers
    #        See PaymentException and payment_exception_handler for more information.
    return JSONResponse(status_code=status_code, content=jsonable_encoder(resp_blob))
