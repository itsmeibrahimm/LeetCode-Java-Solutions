from datetime import datetime
from unittest.mock import MagicMock
import uuid
from app.payin.core.cart_payment.model import (
    PaymentIntent,
    PgpPaymentIntent,
    CartPayment,
    CartMetadata,
    CartType,
)
from app.payin.core.cart_payment.types import IntentStatus


class FunctionMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(FunctionMock, self).__call__(*args, **kwargs)


class ContextMock(MagicMock):
    async def __aenter__(self, *args, **kwargs):
        pass

    async def __aexit__(self, *args, **kwargs):
        pass


def generate_payment_intent(
    cart_payment_id: uuid.UUID = uuid.uuid4(),
    status: str = "init",
    capture_method: str = "manual",
    confirmation_method: str = "manual",
):
    return PaymentIntent(
        id=uuid.uuid4(),
        cart_payment_id=cart_payment_id,
        idempotency_key=str(uuid.uuid4()),
        amount_initiated=0,
        amount=0,
        amount_capturable=0,
        amount_received=0,
        application_fee_amount=0,
        capture_method=capture_method,
        confirmation_method=confirmation_method,
        country="US",
        currency="USD",
        status=IntentStatus(status),
        statement_descriptor="descriptor",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=None,
        cancelled_at=None,
    )


def generate_pgp_payment_intent(
    status: str = "init", capture_method: str = "manual"
) -> PgpPaymentIntent:
    return PgpPaymentIntent(
        id=uuid.uuid4(),
        payment_intent_id=uuid.uuid4(),
        idempotency_key=str(uuid.uuid4()),
        provider="Stripe",
        resource_id=str(uuid.uuid4()),
        status=IntentStatus(status),
        invoice_resource_id=None,
        charge_resource_id=None,
        payment_method_resource_id=str(uuid.uuid4),
        currency="USD",
        amount=0,
        amount_capturable=0,
        amount_received=0,
        application_fee_amount=0,
        payout_account_id=str(uuid.uuid4()),
        capture_method=capture_method,
        confirmation_method="manual",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=None,
        cancelled_at=None,
    )


def generate_cart_payment(
    payer_id: str = str(uuid.uuid4()), payment_method_id: str = str(uuid.uuid4())
) -> CartPayment:
    return CartPayment(
        id=uuid.uuid4(),
        amount=500,
        payer_id=payer_id,
        payment_method_id=payment_method_id,
        capture_method="manual",
        cart_metadata=CartMetadata(
            reference_id=0, ct_reference_id=0, type=CartType.ORDER_CART
        ),
    )
