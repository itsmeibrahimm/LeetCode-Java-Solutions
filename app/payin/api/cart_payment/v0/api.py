import typing
from datetime import datetime

from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.payin.api.cart_payment.v0.converter import (
    to_internal_cart_payment,
    to_external_cart_payment,
    to_internal_legacy_payment_info,
)
from app.payin.api.cart_payment.v0.request import (
    CreateCartPaymentLegacyRequest,
    UpdateCartPaymentLegacyRequest,
)
from app.payin.api.cart_payment.v0.response import (
    LegacyCartPayment,
    CreateCartPaymentLegacyResponse,
)
from app.payin.api.commando_mode import (
    commando_route_dependency,
    override_commando_mode_legacy_cart_payment,
)
from app.payin.core.cart_payment.model import CartPayment, CartPaymentList
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.types import LegacyConsumerChargeId
from app.payin.core.payment_method.types import CartPaymentSortKey

api_tags = ["CartPaymentV0"]
router = APIRouter()


@router.post(
    "/cart_payments",
    response_model=CreateCartPaymentLegacyResponse,
    status_code=HTTP_201_CREATED,
    operation_id="CreateCartPayment",
    tags=api_tags,
)
async def create_cart_payment(
    cart_payment_request: CreateCartPaymentLegacyRequest = Depends(
        override_commando_mode_legacy_cart_payment
    ),
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    log.info("Creating cart_payment for legacy client.")

    cart_payment, legacy_consumer_charge_id = await cart_payment_processor.create_cart_payment_v0(
        request_cart_payment=to_internal_cart_payment(cart_payment_request),
        legacy_payment=to_internal_legacy_payment_info(
            cart_payment_request.legacy_payment
        ),
        idempotency_key=cart_payment_request.idempotency_key,
        payment_country=cart_payment_request.payment_country,
        payer_country=cart_payment_request.payer_country,
        currency=cart_payment_request.currency,
    )

    log.info("Created cart_payment for legacy client.", cart_payment_id=cart_payment.id)
    return to_external_cart_payment(
        cart_payment=cart_payment, legacy_consumer_charge_id=legacy_consumer_charge_id
    )


@router.post(
    "/cart_payments/{dd_charge_id}/adjust",
    response_model=CartPayment,
    status_code=HTTP_200_OK,
    operation_id="AdjustCartPayment",
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
    cart_payment: CartPayment = await cart_payment_processor.update_payment_for_legacy_charge(
        idempotency_key=cart_payment_request.idempotency_key,
        dd_charge_id=dd_charge_id,
        amount=cart_payment_request.amount,
        client_description=cart_payment_request.client_description,
        dd_additional_payment_info=cart_payment_request.dd_additional_payment_info,
        split_payment=cart_payment_request.split_payment,
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
    tags=api_tags,
)
async def cancel_cart_payment(
    dd_charge_id: int,
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


@router.get(
    "/cart_payments",
    response_model=CartPaymentList,
    status_code=HTTP_200_OK,
    operation_id="ListCartPayment",
    tags=api_tags,
    dependencies=[Depends(commando_route_dependency)],
)
async def list_cart_payments(
    dd_consumer_id: int,
    created_at_gte: datetime = None,
    created_at_lte: datetime = None,
    sort_by: CartPaymentSortKey = CartPaymentSortKey.CREATED_AT,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
) -> CartPaymentList:
    try:
        return await cart_payment_processor.list_legacy_cart_payment(
            dd_consumer_id=dd_consumer_id,
            created_at_gte=created_at_gte,
            created_at_lte=created_at_lte,
            sort_by=sort_by,
        )
    except PaymentError:
        log.warn("[list_cart_payments] PaymentError")
        raise


@router.get(
    "/cart_payments/get_by_charge_id",
    response_model=LegacyCartPayment,
    status_code=HTTP_200_OK,
    operation_id="GetCartPayment",
    tags=api_tags,
    dependencies=[Depends(commando_route_dependency)],
)
async def get_cart_payment(
    dd_charge_id: int,
    log: BoundLogger = Depends(get_logger_from_req),
    cart_payment_processor: CartPaymentProcessor = Depends(CartPaymentProcessor),
):
    """
    Get an existing cart payment.
    - **dd_charge_id**: charge id for a cart payment.
    """
    log.info("Getting cart payment", dd_charge_id=dd_charge_id)
    cart_payment = await cart_payment_processor.legacy_get_cart_payment(
        dd_charge_id=dd_charge_id
    )
    log.info("Cart payment retrieved", dd_charge_id=dd_charge_id)
    return to_external_cart_payment(
        cart_payment=cart_payment,
        legacy_consumer_charge_id=typing.cast(LegacyConsumerChargeId, dd_charge_id),
    )
