from fastapi.encoders import jsonable_encoder
from pydantic import Schema
from starlette.requests import Request
from starlette.responses import JSONResponse
from structlog import BoundLogger

from app.commons.api.exceptions import payment_http_exception_handler
from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.context.req_context import response_with_req_id, get_logger_from_req
from app.middleware.doordash_metrics import get_endpoint_from_scope
from app.payin.core.exceptions import PayinErrorCode

__all__ = ["PayinErrorResponse", "payin_error_handler"]


class PayinErrorResponse(PaymentErrorResponseBody):
    """
    Payin service error response
    """

    error_code: PayinErrorCode = Schema(  # type: ignore
        default=..., description=str(PayinErrorCode.__doc__)
    )
    retryable: bool = Schema(  # type: ignore
        default=..., description="whether client can retry on this error"
    )
    error_message: str = Schema(  # type: ignore
        default=...,
        description="descriptive message for client to understand more about the error. "
        "client should NEVER rely on error message in their codified business logic",
    )


async def payin_error_handler(request: Request, payment_exception: PaymentException):
    if PayinErrorCode.known_value(payment_exception.error_code):
        logger: BoundLogger = get_logger_from_req(request)
        endpoint = get_endpoint_from_scope(request.scope)
        error_response = jsonable_encoder(
            PayinErrorResponse(
                error_code=PayinErrorCode(payment_exception.error_code),
                error_message=payment_exception.error_message,
                retryable=payment_exception.retryable,
            )
        )

        logger.info(
            "api exception handler",
            type="payment error",
            endpoint=endpoint,
            status_code=payment_exception.status_code,
            error=error_response,
            retryable=payment_exception.retryable,
        )

        return response_with_req_id(
            request,
            JSONResponse(
                status_code=payment_exception.status_code, content=error_response
            ),
        )
    else:
        # todo: this is for backward compatibility,
        # in next revision, will remove the need to handle payment exception and update to directly
        # handle payment error, then we don't need this if condition
        return payment_http_exception_handler(request, payment_exception)
