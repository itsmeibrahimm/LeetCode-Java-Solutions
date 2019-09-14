from app.payin.api.cart_payment.base.request import CreateCartPaymentBaseRequest
from app.commons.core.errors import PaymentError
from app.payin.core.exceptions import PayinErrorCode
from app.payin.core.cart_payment.model import CartPayment, CorrelationIds, SplitPayment

from pydantic import ValidationError

from uuid import uuid4


def create_request_to_model(
    cart_payment_request: CreateCartPaymentBaseRequest
) -> CartPayment:
    try:
        if (
            hasattr(cart_payment_request, "correlation_ids")
            and cart_payment_request.correlation_ids
        ):
            correlation_ids = CorrelationIds(
                reference_id=cart_payment_request.correlation_ids.reference_id,
                reference_type=cart_payment_request.correlation_ids.reference_type,
            )
        else:
            # Placeholders for legacy case.  See v0 handling within CartPaymentProcessor.create_payment.
            # This will be removed once the legacy path is deprecated.
            correlation_ids = CorrelationIds(reference_id="", reference_type="")

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
