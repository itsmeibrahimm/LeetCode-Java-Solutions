from typing import Any, Dict

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.context.logger import get_logger
from app.commons.context.req_context import response_with_req_id

# used for customized FastAPI exception translator
api_error_translator_log = get_logger("api_error_translator")


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


async def payment_http_exception_handler(
    request: Request, exception: StarletteHTTPException
):
    """
    Payment http exception handler.
    As .PaymentException is a subclass of fastapi.HTTPException,
    we are overriding default FastAPI http_exception_handler here in a way that:
    1. If a thrown HTTPException is an instance of PaymentException, then we handle it in our customized way
    2. If a thrown HTTPException is only an instance of HTTPException, then we just let
    default http_exception_handler handle it

    Note:
    1. This http exception handler shall be added at each sub-app level, since sub app's ExceptionMiddleWare will
    handler exceptions earlier than root app.
    2. Although PaymentException is a subclass of fastapi.HTTPException, when register this exception handler
    we should register it to handle starlette.exceptions.HTTPException.
    Why? see: https://fastapi.tiangolo.com/tutorial/handling-errors/#fastapis-httpexception-vs-starlettes-httpexception

    example:
    app = FastAPI()
    app.add_exception_handler(starlette.exceptions.HTTPException, payment_http_exception_handler)

    OR as a short cut, use:
    app.commons.error.errors.register_payment_exception_handler(app)

    See FastAPI error handling about re-use / override default http exception handler:
    https://fastapi.tiangolo.com/tutorial/handling-errors/#re-use-fastapis-exception-handlers

    :param request: starlette.Request
    :param exception: starlette.exceptions.HTTPException
    :return: Handled Http exception response
    """
    exception_response = None
    if isinstance(exception, PaymentException):
        # we wrapped the error, provide some additional info
        error = PaymentErrorResponseBody(
            error_code=exception.error_code,
            error_message=exception.error_message,
            retryable=exception.retryable,
        )
        api_error_translator_log.info(
            exception.__class__.__name__,
            status_code=exception.status_code,
            error=error.dict(),
        )
        exception_response = JSONResponse(
            status_code=exception.status_code, content=jsonable_encoder(error)
        )
    else:
        # default HTTP exception handling from the framework (eg. 404)
        # report un modeled http exception to sentry with error log level
        api_error_translator_log.error(
            exception.__class__.__name__,
            status_code=exception.status_code,
            exc_info=exception,
        )
        exception_response = await http_exception_handler(request, exception)

    return response_with_req_id(request, exception_response)


async def payment_internal_error_handler(
    request: Request, exception: Exception
) -> Response:

    # unhandled error, report this in sentry and newrelic
    api_error_translator_log.error(exception.__class__.__name__, exc_info=exception)

    return response_with_req_id(
        request,
        JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(
                PaymentErrorResponseBody(
                    error_code="unknown_internal_error",
                    error_message="Internal Server Error",
                    retryable=False,
                )
            ),
        ),
    )


def _get_error_field_path(error: Dict[str, Any]) -> str:
    path_components = error.get("loc", [])
    if hasattr(path_components, "__iter__"):
        return ".".join(component for component in path_components)
    return str(path_components)


def _build_field_error_display(error: Dict[str, Any]) -> str:
    return f"{_get_error_field_path(error)}: {error.get('msg', 'validation failed')}"


def _build_request_validation_error_display(validation_error: ValidationError) -> str:
    error_count = len(validation_error.errors())
    field_errors = "; ".join(
        _build_field_error_display(error) for error in validation_error.errors()
    )
    return (
        f"{error_count} request validation error{'s' if error_count > 1 else ''}"
        f" for {validation_error.model.__name__}. {field_errors}"
    )


async def payment_request_validation_exception_handler(
    request: Request, exception: RequestValidationError
) -> JSONResponse:
    # log the details of the validation error

    api_error_translator_log.info(
        exception.__class__.__name__, validation_errors=exception.errors()
    )

    return response_with_req_id(
        request,
        JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                PaymentErrorResponseBody(
                    error_code="request_validation_error",
                    error_message=_build_request_validation_error_display(exception),
                    retryable=False,
                )
            ),
        ),
    )


def register_base_payment_exception_handler(app: FastAPI):
    app.add_exception_handler(StarletteHTTPException, payment_http_exception_handler)
    app.add_exception_handler(
        RequestValidationError, payment_request_validation_exception_handler
    )
    app.add_exception_handler(Exception, payment_internal_error_handler)
