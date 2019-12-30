from uuid import uuid4

from pydantic import ValidationError

from app.payin.api.cart_payment.v0.request import CreateCartPaymentLegacyRequest
from app.payin.api.cart_payment.v0.response import CreateCartPaymentLegacyResponse
from app.payin.core.cart_payment.model import CartPayment, LegacyPayment
from app.payin.core.cart_payment.types import LegacyConsumerChargeId
from app.payin.core.exceptions import PayinError, PayinErrorCode
from app.payin.core.payer.model import PayerCorrelationIds
from app.payin.core.types import (
    LegacyPaymentInfo as RequestLegacyPaymentInfo,
    PayerReferenceIdType,
)


def to_internal_cart_payment(
    cart_payment_request: CreateCartPaymentLegacyRequest
) -> CartPayment:
    try:
        return CartPayment(
            id=uuid4(),
            payer_id=None,
            payer_correlation_ids=PayerCorrelationIds(
                payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
                payer_reference_id=str(
                    cart_payment_request.legacy_payment.dd_consumer_id
                ),
            ),
            amount=cart_payment_request.amount,
            payment_method_id=None,
            delay_capture=cart_payment_request.delay_capture,
            correlation_ids=cart_payment_request.legacy_correlation_ids,
            metadata=None,
            client_description=cart_payment_request.client_description,
            payer_statement_description=cart_payment_request.payer_statement_description,
            split_payment=cart_payment_request.split_payment,
            created_at=None,
            updated_at=None,
        )
    except ValidationError as validation_error:
        raise PayinError(
            error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA
        ) from validation_error


def to_internal_legacy_payment_info(
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


def to_external_cart_payment(
    cart_payment: CartPayment, legacy_consumer_charge_id: LegacyConsumerChargeId
) -> CreateCartPaymentLegacyResponse:
    return CreateCartPaymentLegacyResponse(
        dd_charge_id=legacy_consumer_charge_id,
        id=cart_payment.id,
        amount=cart_payment.amount,
        payer_id=cart_payment.payer_id,
        payer_correlation_ids=cart_payment.payer_correlation_ids,
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
