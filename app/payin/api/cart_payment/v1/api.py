from fastapi import APIRouter

from app.commons.context.req_context import get_context_from_req
from app.commons.context.app_context import get_context_from_app
from app.payin.api.cart_payment.v1.request import CartPaymentRequest
from app.payin.core.cart_payment.processor import submit_payment
from app.payin.core.cart_payment.model import (
    CartPayment,
    CartMetadata,
    CartType,
    SplitPayment,
    LegacyPayment,
)
from app.payin.repository.cart_payment_repo import CartPaymentRepository

from starlette.status import HTTP_201_CREATED
from starlette.requests import Request


def create_cart_payments_router(cart_payment_repo: CartPaymentRepository) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/cart_payments", status_code=HTTP_201_CREATED)
    async def create_payer(cart_payment_request: CartPaymentRequest, request: Request):
        req_context = get_context_from_req(request)
        app_context = get_context_from_app(request.app)
        req_context.log.debug(
            f"Creating cart_payment for payer {cart_payment_request.payer_id}"
        )

        # TODO: Validate amount does not exceed configured max for specified currency
        # TODO: Validate payer_id is valid
        # TODO: Validate payer_id can access payment_method_id

        cart_payment: CartPayment = await submit_payment(
            app_context,
            req_context,
            cart_payment_repo,
            request_to_model(cart_payment_request),
            cart_payment_request.idempotency_key,
            cart_payment_request.country,
            cart_payment_request.currency,
            cart_payment_request.client_description,
        )

        req_context.log.info(
            f"Created cart_payment {cart_payment.id} of type {cart_payment.cart_metadata.type} for payer {cart_payment.payer_id}"
        )
        return cart_payment

    return router


def request_to_model(cart_payment_request: CartPaymentRequest) -> CartPayment:
    # TODO review duplication among types here
    return CartPayment(
        id=None,
        payer_id=cart_payment_request.payer_id,
        amount=cart_payment_request.amount,
        payment_method_id=cart_payment_request.payment_method_id,
        capture_method=cart_payment_request.capture_method,
        cart_metadata=CartMetadata(
            reference_id=cart_payment_request.metadata.reference_id,
            ct_reference_id=cart_payment_request.metadata.ct_reference_id,
            type=CartType(cart_payment_request.metadata.type),
        ),
        client_description=cart_payment_request.client_description,
        payer_statement_description=cart_payment_request.payer_statement_description,
        legacy_payment=LegacyPayment(
            consumer_id=getattr(
                cart_payment_request.legacy_payment, "consumer_id", None
            ),
            charge_id=getattr(cart_payment_request.legacy_payment, "charge_id", None),
            stripe_customer_id=getattr(
                cart_payment_request.legacy_payment, "stripe_customer_id", None
            ),
        ),
        split_payment=SplitPayment(
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
