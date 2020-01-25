from uuid import uuid4

from pydantic import ValidationError

from app.payin.api.cart_payment.v1.request import (
    CorrelationIds,
    CreateCartPaymentRequestV1,
)
from app.payin.core.cart_payment.model import CartPayment
from app.payin.core.exceptions import PayinError, PayinErrorCode


def validate_cart_payment_request_v1(cart_payment_request: CreateCartPaymentRequestV1):
    number_of_payment_method_ids: int = int(
        bool(cart_payment_request.payment_method_id)
    ) + int(bool(cart_payment_request.payment_method_token)) + int(
        bool(cart_payment_request.dd_stripe_card_id)
    )

    if number_of_payment_method_ids != 1:
        raise ValueError(
            f"only 1 of payment method identifiers should be provided but found "
            f"payment_method_id={cart_payment_request.payment_method_id}, "
            f"payment_method_token={cart_payment_request.payment_method_token}, "
            f"dd_stripe_card_id={cart_payment_request.dd_stripe_card_id}"
        )


def to_internal_cart_payment(
    cart_payment_request: CreateCartPaymentRequestV1, correlation_ids: CorrelationIds
) -> CartPayment:

    validate_cart_payment_request_v1(cart_payment_request)

    try:
        return CartPayment(
            id=uuid4(),
            payer_id=cart_payment_request.payer_id,
            payer_correlation_ids=cart_payment_request.payer_correlation_ids,
            amount=cart_payment_request.amount,
            payment_method_id=cart_payment_request.payment_method_id,
            delay_capture=cart_payment_request.delay_capture,
            correlation_ids=correlation_ids,
            metadata=cart_payment_request.metadata,
            client_description=cart_payment_request.client_description,
            payer_statement_description=cart_payment_request.payer_statement_description,
            split_payment=cart_payment_request.split_payment,
            created_at=None,
            updated_at=None,
            deferred=None,
        )
    except ValidationError as validation_error:
        raise PayinError(
            error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA
        ) from validation_error
