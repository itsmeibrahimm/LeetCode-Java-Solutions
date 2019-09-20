from abc import ABC
from typing import Any

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


class PaymentRequest(BaseModel, ABC):
    """
    Base pydantic request model for all payment service APIs
    """

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)

        # Does not allow specifying an instance of request without any specified field value
        # todo consider move this to a base model shared across payment repo
        if __pydantic_self__.fields and (not __pydantic_self__.__fields_set__):
            raise RequestValidationError(
                f"At least 1 field need to be specified in model={type(__pydantic_self__)}"
            )

    def __init_subclass__(cls, *args, **kwargs):
        # enforce only None is allowed as default
        # 1. since we currently heavily rely on .dict(skip_default=True) to avoid unexpected behavior
        # 2. also defaulting behavior should be driven by biz logic code other than plain object. it makes
        # sense to ensure client always explicitly set what they want
        for field in cls.__fields__.values():
            if field.default is not None:
                raise ValueError(
                    f"only default=None is allowed for field, "
                    f"but found field={field.name} default={field.default} model={cls}"
                )


class PaymentResponse(BaseModel, ABC):
    """
    Base pydantic response model for all payment service APIs
    """

    def __init_subclass__(cls, **kwargs):
        # enforce only None is allowed as default
        # since we currently heavily rely on .dict(skip_default=True) to avoid unexpected behavior
        for field in cls.__fields__.values():
            if field.default is not None:
                raise ValueError(
                    f"only default=None is allowed for field, "
                    f"but found field={field.name} default={field.default} model={cls}"
                )


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

    :param error_code: payment service predefined client-facing error codes.
    :param error_message: friendly error message for client reference.
    :param retryable: identify if the error is retryable or not.
    """

    error_code: str
    error_message: str
    retryable: bool


class UnknownInternalException(PaymentException):
    pass


DEFAULT_INTERNAL_EXCEPTION = UnknownInternalException(
    http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    error_code="unknown_payment_internal_error",
    error_message="payment service encountered unknown internal error",
    retryable=False,
)
