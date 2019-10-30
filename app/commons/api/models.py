from abc import ABC
from typing import Any

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Schema
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.commons.api.errors import (
    InvalidRequestErrorCode,
    PaymentErrorCode,
    payment_error_message_maps,
)


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

    error_code: str = Schema(  # type: ignore
        default=...,
        description="codified payment service error code that client can consume programmatically",
    )
    retryable: bool = Schema(  # type: ignore
        default=..., description="whether client can retry on this error"
    )
    error_message: str = Schema(  # type: ignore
        default=...,
        description="descriptive message for client to understand more about the error. "
        "client should NEVER rely on error message in their codified business logic",
    )


class BadRequestError(PaymentException):
    def __init__(self, error_code, err_message):
        super().__init__(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=error_code,
            error_message=err_message,
            retryable=True,
        )


class InvalidRequestError(PaymentException):
    def __init__(self, error_code: InvalidRequestErrorCode):
        super().__init__(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=error_code,
            error_message=payment_error_message_maps[error_code],
            retryable=False,
        )


class NotFoundError(PaymentException):
    def __init__(self,):
        super().__init__(
            http_status_code=HTTP_404_NOT_FOUND,
            error_code=PaymentErrorCode.NOT_FOUND_ERROR,
            error_message=payment_error_message_maps[PaymentErrorCode.NOT_FOUND_ERROR],
            retryable=False,
        )


class RateLimitError(PaymentException):
    def __init__(self):
        super().__init__(
            http_status_code=HTTP_429_TOO_MANY_REQUESTS,
            error_code=PaymentErrorCode.RATE_LIMIT_ERROR,
            error_message=payment_error_message_maps[PaymentErrorCode.RATE_LIMIT_ERROR],
            retryable=True,
        )


class AuthenticationError(PaymentException):
    def __init__(self):
        super().__init__(
            http_status_code=HTTP_401_UNAUTHORIZED,
            error_code=PaymentErrorCode.AUTHENTICATION_ERROR,
            error_message=payment_error_message_maps[
                PaymentErrorCode.AUTHENTICATION_ERROR
            ],
            retryable=False,
        )


class AuthorizationError(PaymentException):
    def __init__(self):
        super().__init__(
            http_status_code=HTTP_403_FORBIDDEN,
            error_code=PaymentErrorCode.AUTHORIZATION_ERROR,
            error_message=payment_error_message_maps[
                PaymentErrorCode.AUTHORIZATION_ERROR
            ],
            retryable=False,
        )


class InternalServerError(PaymentException):
    def __init__(self):
        super().__init__(
            http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=PaymentErrorCode.UNKNOWN_INTERNAL_ERROR,
            error_message=payment_error_message_maps[
                PaymentErrorCode.UNKNOWN_INTERNAL_ERROR
            ],
            retryable=False,
        )


DEFAULT_INTERNAL_EXCEPTION = InternalServerError()
