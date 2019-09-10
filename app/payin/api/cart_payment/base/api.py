from app.payin.api.cart_payment.base.request import CreateCartPaymentBaseRequest
from app.commons.core.errors import PaymentError
from app.payin.core.exceptions import PayinErrorCode
from app.payin.core.types import LegacyPaymentInfo as RequestLegacyPaymentInfo
from app.payin.core.cart_payment.model import (
    CartPayment,
    CartMetadata,
    CartType,
    SplitPayment,
    LegacyPayment,
)

from pydantic import ValidationError
from typing import Optional
from uuid import uuid4


def create_request_to_model(
    cart_payment_request: CreateCartPaymentBaseRequest
) -> CartPayment:
    try:
        return CartPayment(
            id=uuid4(),
            payer_id=getattr(cart_payment_request, "payer_id", None),
            amount=cart_payment_request.amount,
            payment_method_id=getattr(cart_payment_request, "payment_method_id", None),
            delay_capture=cart_payment_request.delay_capture,
            cart_metadata=CartMetadata(
                reference_id=cart_payment_request.cart_metadata.reference_id,
                reference_type=cart_payment_request.cart_metadata.reference_type,
                type=CartType(cart_payment_request.cart_metadata.type),
            ),
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


def get_legacy_payment_model(
    request_legacy_payment_info: Optional[RequestLegacyPaymentInfo]
) -> Optional[LegacyPayment]:
    if not request_legacy_payment_info:
        return None

    return LegacyPayment(
        dd_consumer_id=request_legacy_payment_info.dd_consumer_id,
        dd_stripe_card_id=request_legacy_payment_info.dd_stripe_card_id,
        dd_country_id=request_legacy_payment_info.dd_country_id,
        stripe_customer_id=getattr(
            request_legacy_payment_info, "stripe_customer_id", None
        ),
        stripe_payment_method_id=getattr(
            request_legacy_payment_info, "stripe_payment_method_id", None
        ),
        stripe_card_id=getattr(request_legacy_payment_info, "stripe_card_id", None),
    )
