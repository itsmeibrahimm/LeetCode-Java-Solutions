from uuid import uuid4

from pydantic import ValidationError

from app.commons.core.errors import PaymentError
from app.payin.api.cart_payment.base.request import CreateCartPaymentBaseRequest
from app.payin.core.cart_payment.model import CartPayment, CorrelationIds, SplitPayment
from app.payin.core.exceptions import PayinErrorCode


def create_request_to_model(
    cart_payment_request: CreateCartPaymentBaseRequest, correlation_ids: CorrelationIds
) -> CartPayment:
    try:
        return CartPayment(
            id=uuid4(),
            payer_id=getattr(cart_payment_request, "payer_id", None),
            amount=cart_payment_request.amount,
            payment_method_id=getattr(cart_payment_request, "payment_method_id", None),
            delay_capture=cart_payment_request.delay_capture,
            correlation_ids=correlation_ids,
            metadata=getattr(cart_payment_request, "metadata", None),
            client_description=cart_payment_request.client_description,
            payer_statement_description=cart_payment_request.payer_statement_description,
            split_payment=None
            if not cart_payment_request.split_payment
            else SplitPayment(
                payout_account_id=getattr(
                    cart_payment_request.split_payment, "payout_account_id", None
                ),
                application_fee_amount=getattr(
                    cart_payment_request.split_payment, "application_fee_amount", None
                ),
            ),
            created_at=None,
            updated_at=None,
        )
    except ValidationError as validation_error:
        raise PaymentError(
            error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
            error_message=str(validation_error),
            retryable=False,
        )
