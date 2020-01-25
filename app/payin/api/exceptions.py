from typing import Dict, Set

from fastapi.encoders import jsonable_encoder
from pydantic import Schema
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.commons.api.exceptions import api_error_translator_log
from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.context.req_context import response_with_req_id
from app.commons.core.errors import PaymentError
from app.payin.core.exceptions import PayinError, PayinErrorCode

__all__ = ["PayinErrorResponse", "payin_error_handler"]

# Mapping from http status code to payin error code
_status_code_to_payin_error_code: Dict[int, Set[PayinErrorCode]] = {
    status.HTTP_404_NOT_FOUND: {
        PayinErrorCode.CART_PAYMENT_NOT_FOUND,
        PayinErrorCode.CART_PAYMENT_NOT_FOUND_FOR_CHARGE_ID,
        PayinErrorCode.PAYER_READ_NOT_FOUND,
        PayinErrorCode.PAYER_UPDATE_NOT_FOUND,
        PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND,
        PayinErrorCode.DISPUTE_NOT_FOUND,
        PayinErrorCode.PAYER_READ_STRIPE_ERROR_NOT_FOUND,
    },
    status.HTTP_403_FORBIDDEN: {
        PayinErrorCode.CART_PAYMENT_OWNER_MISMATCH,
        PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH,
        PayinErrorCode.COMMANDO_DISABLED_ENDPOINT,
        PayinErrorCode.PAYMENT_INTENT_CREATE_INVALID_PROVIDER_PAYMENT_METHOD,
    },
    status.HTTP_400_BAD_REQUEST: {
        PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
        PayinErrorCode.CART_PAYMENT_DATA_INVALID,
        PayinErrorCode.CART_PAYMENT_AMOUNT_INVALID,
        PayinErrorCode.CART_PAYMENT_PAYMENT_METHOD_NOT_FOUND,
        PayinErrorCode.CART_PAYMENT_CONCURRENT_ACCESS_ERROR,
        PayinErrorCode.PAYER_CREATE_INVALID_DATA,
        PayinErrorCode.PAYER_CREATE_PAYER_ALREADY_EXIST,
        PayinErrorCode.PAYER_READ_INVALID_DATA,
        PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA,
        PayinErrorCode.PAYER_UPDATE_INVALID_PAYER_TYPE,
        PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_DECLINED_ERROR,
        PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_EXPIRED_ERROR,
        PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_PROCESSING_ERROR,
        PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_INCORRECT_NUMBER_ERROR,
        PayinErrorCode.PAYMENT_INTENT_CREATE_INVALID_SPLIT_PAYMENT_ACCOUNT,
        PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_INCORRECT_CVC_ERROR,
        PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_DATA,
        PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE,
        PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_INPUT,
        PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYER_REFERENCE_ID,
        PayinErrorCode.DISPUTE_READ_INVALID_DATA,
        PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS,
        PayinErrorCode.DISPUTE_LIST_NO_ID_PARAMETERS,
        PayinErrorCode.DISPUTE_LIST_MORE_THAN_ID_ONE_PARAMETER,
        PayinErrorCode.DISPUTE_NO_STRIPE_CARD_FOR_STRIPE_ID,
        PayinErrorCode.DISPUTE_NO_CONSUMER_CHARGE_FOR_STRIPE_DISPUTE,
        PayinErrorCode.DISPUTE_NO_PAYER_FOR_PAYER_ID,
        PayinErrorCode.DISPUTE_NO_STRIPE_CARD_FOR_PAYMENT_METHOD_ID,
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        PayinErrorCode.PAYER_CREATE_STRIPE_ERROR,
        PayinErrorCode.PAYER_READ_DB_ERROR,
        PayinErrorCode.PAYER_UPDATE_STRIPE_ERROR,
        PayinErrorCode.PAYER_UPDATE_DB_ERROR,
        PayinErrorCode.PAYER_READ_STRIPE_ERROR,
        PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR,
        PayinErrorCode.PAYMENT_INTENT_CAPTURE_STRIPE_ERROR,
        PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR,
        PayinErrorCode.PAYMENT_INTENT_CREATE_ERROR,
        PayinErrorCode.PAYMENT_METHOD_CREATE_DB_ERROR,
        PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR,
        PayinErrorCode.PAYMENT_METHOD_CREATE_STRIPE_ERROR,
        PayinErrorCode.PAYMENT_METHOD_DELETE_STRIPE_ERROR,
        PayinErrorCode.PAYMENT_METHOD_DELETE_DB_ERROR,
        PayinErrorCode.DISPUTE_READ_DB_ERROR,
        PayinErrorCode.DISPUTE_UPDATE_STRIPE_ERROR,
        PayinErrorCode.DISPUTE_UPDATE_DB_ERROR,
    },
    status.HTTP_501_NOT_IMPLEMENTED: {PayinErrorCode.API_NOT_IMPLEMENTED_ERROR},
}


def _populate_error_code_to_status_code() -> Dict[PayinErrorCode, int]:
    result: Dict[PayinErrorCode, int] = {}
    for status_code, error_codes in _status_code_to_payin_error_code.items():
        for error_code in error_codes:
            if error_code in result:
                raise ValueError(
                    f"Duplicate error code status code combination: {error_code}."
                )
            result[error_code] = status_code
    return result


# Mapping from payin error code to http status code
_error_code_to_status_code: Dict[
    PayinErrorCode, int
] = _populate_error_code_to_status_code()


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


async def payin_error_handler(request: Request, error: PaymentError) -> JSONResponse:
    """

    Args:
        request: starlette request
        error: PaymentError raised in application

    Returns: translated PaymentErrorResponse json payload

    """

    if isinstance(error, PayinError):
        error_response = PayinErrorResponse(
            error_code=error.error_code,
            error_message=error.error_message,
            retryable=error.retryable,
        )

        status_code = _error_code_to_status_code.get(
            error.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            api_error_translator_log.error(
                error.__class__.__name__,
                status_code=status_code,
                error=error_response.dict(),
            )
        else:
            api_error_translator_log.info(
                error.__class__.__name__,
                status_code=status_code,
                error=error_response.dict(),
            )

        return response_with_req_id(
            request,
            JSONResponse(
                status_code=status_code, content=jsonable_encoder(error_response)
            ),
        )
    else:
        # if not modeled payin error, will just raise PaymentException and hand over to root level handler to translate
        raise PaymentException(
            error_code=error.error_code,
            error_message=error.error_message,
            retryable=error.retryable,
            http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from error
