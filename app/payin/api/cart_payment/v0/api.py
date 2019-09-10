from fastapi import APIRouter, Depends
from structlog.stdlib import BoundLogger

from app.payin.api.cart_payment.base.api import (
    create_request_to_model,
    get_legacy_payment_model,
)
from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.commons.api.models import PaymentException, PaymentErrorResponseBody
from app.payin.api.cart_payment.v0.request import CreateCartPaymentLegacyRequest
from app.payin.core.exceptions import PayinErrorCode

# from app.payin.core.types import LegacyPaymentInfo as RequestLegacyPaymentInfo
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.model import CartPayment

from starlette.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

api_tags = ["CartPaymentV0"]
router = APIRouter()


@router.post(
    "/cart_payments",
    response_model=CartPayment,
    status_code=HTTP_201_CREATED,
    operation_id="CreateCartPayment",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_403_FORBIDDEN: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    include_in_schema=False,
    tags=api_tags,
)
async def create_cart_payment_for_legacy_client(
    cart_payment_request: CreateCartPaymentLegacyRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    log.info(f"Creating cart_payment for legacy client.")

    try:
        cart_payment = await cart_payment_processor.create_payment(
            request_cart_payment=create_request_to_model(cart_payment_request),
            request_legacy_payment=get_legacy_payment_model(
                cart_payment_request.legacy_payment
            ),
            idempotency_key=cart_payment_request.idempotency_key,
            country=cart_payment_request.payment_country,
            currency=cart_payment_request.currency,
            client_description=cart_payment_request.client_description,
        )

        log.info(
            f"Created cart_payment {cart_payment.id} of type {cart_payment.cart_metadata.type} for legacy client."
        )
        return cart_payment
    except PaymentError as payment_error:
        http_status_code = HTTP_500_INTERNAL_SERVER_ERROR
        if payment_error.error_code == PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND:
            http_status_code = HTTP_400_BAD_REQUEST
        elif (
            payment_error.error_code
            == PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH
        ):
            http_status_code = HTTP_403_FORBIDDEN

        raise PaymentException(
            http_status_code=http_status_code,
            error_code=payment_error.error_code,
            error_message=payment_error.error_message,
            retryable=payment_error.retryable,
        )
