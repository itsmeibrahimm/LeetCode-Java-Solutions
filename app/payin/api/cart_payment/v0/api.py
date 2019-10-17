from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_404_NOT_FOUND,
)
from structlog.stdlib import BoundLogger

from app.commons.api.models import PaymentException, PaymentErrorResponseBody
from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.payin.api.cart_payment.base.request import CancelCartPaymentRequest
from app.payin.api.cart_payment.v0.helper import legacy_create_request_to_model
from app.payin.api.cart_payment.v0.request import (
    CreateCartPaymentLegacyRequest,
    UpdateCartPaymentLegacyRequest,
)
from app.payin.api.cart_payment.v0.response import CreateCartPaymentLegacyResponse
from app.payin.api.commando_mode import (
    commando_route_dependency,
    override_commando_mode_legacy_cart_payment,
)
from app.payin.core.cart_payment.model import CartPayment, LegacyPayment
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.types import LegacyConsumerChargeId
from app.payin.core.exceptions import PayinErrorCode
from app.payin.core.types import LegacyPaymentInfo as RequestLegacyPaymentInfo

api_tags = ["CartPaymentV0"]
router = APIRouter()


@router.post(
    "/cart_payments",
    response_model=CreateCartPaymentLegacyResponse,
    status_code=HTTP_201_CREATED,
    operation_id="CreateCartPayment",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_403_FORBIDDEN: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def create_cart_payment_for_legacy_client(
    cart_payment_request: CreateCartPaymentLegacyRequest = Depends(
        override_commando_mode_legacy_cart_payment
    ),
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    log.info("Creating cart_payment for legacy client.")

    try:
        cart_payment, legacy_consumer_charge_id = await cart_payment_processor.legacy_create_payment(
            request_cart_payment=legacy_create_request_to_model(
                cart_payment_request, cart_payment_request.legacy_correlation_ids
            ),
            legacy_payment=get_legacy_payment_model(
                cart_payment_request.legacy_payment
            ),
            idempotency_key=cart_payment_request.idempotency_key,
            payment_country=cart_payment_request.payment_country,
            payer_country=cart_payment_request.payer_country,
            currency=cart_payment_request.currency,
        )

        log.info(
            "Created cart_payment for legacy client.", cart_payment_id=cart_payment.id
        )
        return form_create_response(
            cart_payment=cart_payment,
            legacy_consumer_charge_id=legacy_consumer_charge_id,
        )
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


@router.post(
    "/cart_payments/{dd_charge_id}/adjust",
    response_model=CartPayment,
    status_code=HTTP_200_OK,
    operation_id="AdjustCartPayment",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_403_FORBIDDEN: {"model": PaymentErrorResponseBody},
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
    dependencies=[Depends(commando_route_dependency)],
)
async def update_cart_payment(
    dd_charge_id: int,
    cart_payment_request: UpdateCartPaymentLegacyRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    log.info(
        "Updating cart_payment associated with legacy consumer charge.",
        dd_charge_id=dd_charge_id,
        cart_payment_request=cart_payment_request,
    )
    try:
        cart_payment: CartPayment = await cart_payment_processor.update_payment_for_legacy_charge(
            idempotency_key=cart_payment_request.idempotency_key,
            dd_charge_id=dd_charge_id,
            amount=cart_payment_request.amount,
            client_description=cart_payment_request.client_description,
            dd_additional_payment_info=cart_payment_request.dd_additional_payment_info,
            split_payment=cart_payment_request.split_payment,
        )
    except PaymentError as payment_error:
        http_status_code = HTTP_500_INTERNAL_SERVER_ERROR
        if payment_error.error_code == PayinErrorCode.CART_PAYMENT_NOT_FOUND:
            http_status_code = HTTP_404_NOT_FOUND
        elif payment_error.error_code == PayinErrorCode.CART_PAYMENT_OWNER_MISMATCH:
            http_status_code = HTTP_403_FORBIDDEN

        raise PaymentException(
            http_status_code=http_status_code,
            error_code=payment_error.error_code,
            error_message=payment_error.error_message,
            retryable=payment_error.retryable,
        )
    log.info(
        "Updated cart_payment for legacy charge",
        cart_payment_id=cart_payment.id,
        dd_charge_id=dd_charge_id,
    )
    return cart_payment


@router.post(
    "/cart_payments/{dd_charge_id}/cancel",
    response_model=CartPayment,
    status_code=HTTP_200_OK,
    operation_id="CancelCartPayment",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_403_FORBIDDEN: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
    dependencies=[Depends(commando_route_dependency)],
)
async def cancel_cart_payment(
    dd_charge_id: int,
    cart_payment_request: CancelCartPaymentRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    """
    Cancel an existing cart payment.  If the payment method associated with the cart payment was
    charged, a full refund is issued.
    """
    log.info("Cancelling cart_payment for legacy charge", dd_charge_id=dd_charge_id)
    cart_payment = await cart_payment_processor.cancel_payment_for_legacy_charge(
        dd_charge_id=dd_charge_id
    )
    log.info("Cancelled cart_payment for legacy charge", dd_charge_id=dd_charge_id)
    return cart_payment


def form_create_response(
    cart_payment: CartPayment, legacy_consumer_charge_id: LegacyConsumerChargeId
) -> CreateCartPaymentLegacyResponse:
    return CreateCartPaymentLegacyResponse(
        dd_charge_id=legacy_consumer_charge_id,
        id=cart_payment.id,
        amount=cart_payment.amount,
        payer_id=cart_payment.payer_id,
        payment_method_id=cart_payment.payment_method_id,
        delay_capture=cart_payment.delay_capture,
        correlation_ids=cart_payment.correlation_ids,
        created_at=cart_payment.created_at,
        updated_at=cart_payment.updated_at,
        client_description=cart_payment.client_description,
        payer_statement_description=cart_payment.payer_statement_description,
        split_payment=cart_payment.split_payment,
        capture_after=cart_payment.capture_after,
        deleted_at=cart_payment.deleted_at,
    )


def get_legacy_payment_model(
    request_legacy_payment_info: RequestLegacyPaymentInfo
) -> LegacyPayment:
    return LegacyPayment(
        dd_consumer_id=request_legacy_payment_info.dd_consumer_id,
        dd_stripe_card_id=request_legacy_payment_info.dd_stripe_card_id,
        dd_country_id=request_legacy_payment_info.dd_country_id,
        dd_additional_payment_info=request_legacy_payment_info.dd_additional_payment_info,
        stripe_customer_id=request_legacy_payment_info.stripe_customer_id,
        stripe_card_id=request_legacy_payment_info.stripe_card_id,
    )
