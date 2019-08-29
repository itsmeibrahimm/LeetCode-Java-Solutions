from fastapi import APIRouter, Depends
from structlog import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.error.errors import (
    PaymentError,
    PaymentException,
    PaymentErrorResponseBody,
)
from app.payin.api.cart_payment.v1.request import (
    CreateCartPaymentRequest,
    UpdateCartPaymentRequest,
)
from app.payin.core.exceptions import PayinErrorCode
from app.payin.core.types import LegacyPaymentInfo as RequestLegacyPaymentInfo
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.model import (
    CartPayment,
    CartMetadata,
    CartType,
    SplitPayment,
    LegacyPayment,
)

from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from typing import Optional
from uuid import UUID, uuid4


api_tags = ["CartPaymentV1"]
router = APIRouter()


@router.post(
    "/api/v1/cart_payments",
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
    - **amount**: [int] amount in cent to charge the cart
    - **payer_country**: [string] payer's country ISO code
    - **currency**: [string] currency to charge the cart
    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id
                             can be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **capture_method**: [string] auto capture or manual (captured by DD payment platform)
    - **idempotency_key**: [string] idempotency key to sumibt the payment
    - **client_description** [string] client description
    - **metadata** [json object] key-value map for cart metadata
    - **metadata.reference_id** [int] DoorDash order_cart id
    - **metadata.ct_reference_id** [int] DoorDash order_cart content-type id
    - **metadata.type** [string] type of reference_id. Valid values are "OrderCart", "Drive", "Subscription"
    - **payer_statement_description** [string] payer_statement_description
    - **legacy_payment** [json object] legacy payment information
    - **split_payment** [json object] information for flow of funds
    - **split_payment.payout_account_id** [string] merchant's payout account id. Now it is stripe_managed_account_id
    - **split_payment.application_fee_amount** [int] fees that we charge merchant on the order

    """

    log.info(f"Creating cart_payment for payer {cart_payment_request.payer_id}")

    try:
        # TODO: use cart_payment_request.payer_country to get stripe platform key
        cart_payment = await cart_payment_processor.submit_payment(
            request_cart_payment=create_request_to_model(cart_payment_request),
            idempotency_key=cart_payment_request.idempotency_key,
            country=cart_payment_request.payment_country,
            currency=cart_payment_request.currency,
            client_description=cart_payment_request.client_description,
        )

        log.info(
            f"Created cart_payment {cart_payment.id} of type {cart_payment.cart_metadata.type} for payer {cart_payment.payer_id}"
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


@router.post(
    "/api/v1/cart_payments/{cart_payment_id}/adjust",
    response_model=CartPayment,
    status_code=HTTP_200_OK,
    operation_id="AdjustCartPayment",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_403_FORBIDDEN: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
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
    - **payer_id**: DoorDash payer_id or stripe_customer_id
    - **amount**: [int] amount in cent to adjust the cart
    - **payer_country**: [string] payer's country ISO code
    - **idempotency_key**: [string] idempotency key to sumibt the payment
    - **client_description** [string] client description
    - **legacy_payment** [json object] legacy payment information
    """
    log.info(f"Updating cart_payment {cart_payment_id}")

    # TODO: use cart_payment_request.payer_country to get stripe platform key
    cart_payment: CartPayment = await cart_payment_processor.update_payment(
        idempotency_key=cart_payment_request.idempotency_key,
        cart_payment_id=cart_payment_id,
        payer_id=cart_payment_request.payer_id,
        amount=cart_payment_request.amount,
        legacy_payment=get_legacy_payment_model(cart_payment_request.legacy_payment),
        client_description=cart_payment_request.client_description,
    )
    log.info(
        f"Updated cart_payment {cart_payment.id} for payer {cart_payment.payer_id}"
    )
    return cart_payment


def create_request_to_model(
    cart_payment_request: CreateCartPaymentRequest
) -> CartPayment:
    return CartPayment(
        id=uuid4(),
        payer_id=cart_payment_request.payer_id if cart_payment_request.payer_id else "",
        amount=cart_payment_request.amount,
        payment_method_id=cart_payment_request.payment_method_id
        if cart_payment_request.payment_method_id
        else "",
        capture_method=cart_payment_request.capture_method,
        cart_metadata=CartMetadata(
            reference_id=cart_payment_request.metadata.reference_id,
            ct_reference_id=cart_payment_request.metadata.ct_reference_id,
            type=CartType(cart_payment_request.metadata.type),
        ),
        client_description=cart_payment_request.client_description,
        payer_statement_description=cart_payment_request.payer_statement_description,
        legacy_payment=get_legacy_payment_model(cart_payment_request.legacy_payment),
        split_payment=None
        if not cart_payment_request.split_payment
        else SplitPayment(
            payout_account_id=getattr(
                cart_payment_request.split_payment, "payout_account_id", None
            ),
            application_fee_amount=getattr(
                cart_payment_request.split_payment, "appication_fee_amount", None
            ),
        ),
        created_at=None,
        updated_at=None,
    )


def get_legacy_payment_model(
    request_legacy_payment_info: Optional[RequestLegacyPaymentInfo]
) -> Optional[LegacyPayment]:
    if not request_legacy_payment_info:
        return None

    return LegacyPayment(
        dd_consumer_id=getattr(request_legacy_payment_info, "dd_consumer_id", None),
        dd_stripe_card_id=getattr(
            request_legacy_payment_info, "dd_stripe_card_id", None
        ),
        dd_charge_id=getattr(request_legacy_payment_info, "dd_charge_id", None),
        stripe_customer_id=getattr(
            request_legacy_payment_info, "stripe_customer_id", None
        ),
        stripe_payment_method_id=getattr(
            request_legacy_payment_info, "stripe_payment_method_id", None
        ),
        stripe_card_id=getattr(request_legacy_payment_info, "stripe_card_id", None),
    )
