from fastapi import APIRouter, Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.commons.api.models import PaymentException, PaymentErrorResponseBody
from app.payin.api.cart_payment.base.request import CancelCartPaymentRequest
from app.payin.api.cart_payment.v1.helper import create_request_to_model
from app.payin.api.cart_payment.v1.request import (
    CreateCartPaymentRequest,
    UpdateCartPaymentRequest,
)
from app.payin.api.commando_mode import commando_route_dependency
from app.payin.core.exceptions import PayinErrorCode
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.model import CartPayment

from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_404_NOT_FOUND,
)
from uuid import UUID


api_tags = ["CartPaymentV1"]
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
    tags=api_tags,
)
async def create_cart_payment(
    cart_payment_request: CreateCartPaymentRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    """
    Create a cart payment.

    - **payer_id**: DoorDash payer_id or stripe_customer_id
    - **amount**: [int] amount in cents for the payment.  Must be greater than 0.
    - **payer_country**: [string] payer's country ISO code.  Example: "US".
    - **payment_country**: [string] country ISO code for where payment is happening.  Example: "US".
    - **currency**: [string] currency for the payment.  Must be a doordash supported currency.  Example: "usd".
    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id
                             can be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **delay_capture**: [bool] whether to capture immediately or delay
    - **idempotency_key**: [string] idempotency key to submit the payment
    - **client_description** [string] client description
    - **metadata** [json object] key-value map for client specified metadata.  Not interpreted, but stored info with cart_payment.
    - **correlation_ids** [json object] Container for referential information to store along with the payment.
    - **correlation_ids.reference_id **- [string] Identifier of external entity this payment is for.  Currently supported: numeric order ID (pass in order ID within this string).
    - **correlation_ids.reference_type **- [string] Type of external identifier provided.  Currently supported: numeric model type ID (pass in type ID within this string).
    - **payer_statement_description** [string] Description that shows up for charge on customer credit card bill.  Max length 22 characters.
    - **split_payment** [json object] information for flow of funds
    - **split_payment.payout_account_id** [string] merchant's payout account id. Now it is stripe_managed_account_id
    - **split_payment.application_fee_amount** [int] fees that we charge merchant on the order

    """

    log.info(f"Creating cart_payment for payer {cart_payment_request.payer_id}")

    try:
        cart_payment = await cart_payment_processor.create_payment(
            # TODO: this should be moved above as a validation/sanitize step and not embedded in the call to processor
            request_cart_payment=create_request_to_model(
                cart_payment_request,
                correlation_ids=cart_payment_request.correlation_ids,
            ),
            idempotency_key=cart_payment_request.idempotency_key,
            payment_country=cart_payment_request.payment_country,
            currency=cart_payment_request.currency,
        )

        log.info(
            f"Created cart_payment {cart_payment.id} for payer {cart_payment.payer_id}"
        )
        # Legacy info not returned for new V1 API
        return cart_payment
    except PaymentError as payment_error:
        log.info(f"exception from create_cart_payment() {payment_error}")
        http_status_code = HTTP_500_INTERNAL_SERVER_ERROR
        if payment_error.error_code in (
            PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND,
            PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
        ):
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
    "/cart_payments/{cart_payment_id}/adjust",
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
    cart_payment_id: UUID,
    cart_payment_request: UpdateCartPaymentRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    """
    Adjust amount of an existing cart payment.

    - **cart_payment_id**: unique cart_payment id
    - **payer_id**: DoorDash payer_id
    - **amount**: [int] The new amount to use for the cart payment, in cents.  This is the new amount (not delta).  Must be greater than 0.
    - **payer_country**: [string] payer's country ISO code
    - **idempotency_key**: [string] idempotency key to sumibt the payment
    - **client_description** [string] client description
    - **split_payment** [json object] Optional, new split payment to use for the payment
    """
    log.info(f"Updating cart_payment {cart_payment_id}")
    try:
        cart_payment = await cart_payment_processor.update_payment(
            idempotency_key=cart_payment_request.idempotency_key,
            cart_payment_id=cart_payment_id,
            payer_id=cart_payment_request.payer_id,
            amount=cart_payment_request.amount,
            client_description=cart_payment_request.client_description,
            split_payment=cart_payment_request.split_payment,
        )
    except PaymentError as payment_error:
        http_status_code = HTTP_500_INTERNAL_SERVER_ERROR
        if payment_error.error_code == PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA:
            http_status_code = HTTP_400_BAD_REQUEST
        elif (
            payment_error.error_code
            == PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH
        ):
            http_status_code = HTTP_403_FORBIDDEN
        elif payment_error.error_code == PayinErrorCode.CART_PAYMENT_NOT_FOUND:
            http_status_code = HTTP_404_NOT_FOUND
        raise PaymentException(
            http_status_code=http_status_code,
            error_code=payment_error.error_code,
            error_message=payment_error.error_message,
            retryable=payment_error.retryable,
        )
    log.info(
        f"Updated cart_payment {cart_payment.id} for payer {cart_payment.payer_id}"
    )
    return cart_payment


@router.post(
    "/cart_payments/{cart_payment_id}/cancel",
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
    cart_payment_id: UUID,
    cart_payment_request: CancelCartPaymentRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    """
    Cancel an existing cart payment.  If the payment method associated with the cart payment was
    charged, a full refund is issued.

    - **cart_payment_id**: ID of cart payment to cancel.
    """
    log.info(f"Cancelling cart_payment {cart_payment_id}")
    try:
        cart_payment = await cart_payment_processor.cancel_payment(
            cart_payment_id=cart_payment_id
        )
    except PaymentError as payment_error:
        http_status_code = HTTP_500_INTERNAL_SERVER_ERROR
        if payment_error.error_code == PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA:
            http_status_code = HTTP_400_BAD_REQUEST
        elif (
            payment_error.error_code
            == PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH
        ):
            http_status_code = HTTP_403_FORBIDDEN
        elif payment_error.error_code == PayinErrorCode.CART_PAYMENT_NOT_FOUND:
            http_status_code = HTTP_404_NOT_FOUND
        raise PaymentException(
            http_status_code=http_status_code,
            error_code=payment_error.error_code,
            error_message=payment_error.error_message,
            retryable=payment_error.retryable,
        )
    log.info(f"Cancelled cart_payment {cart_payment_id}")
    return cart_payment
