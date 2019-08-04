from datetime import datetime
import uuid
from app.payin.core.cart_payment.model import PaymentIntent, PgpPaymentIntent
from app.payin.core.cart_payment.types import (
    PaymentIntentStatus,
    PgpPaymentIntentStatus,
)


def generate_payment_intent(status: str):
    return PaymentIntent(
        id=uuid.uuid4(),
        cart_payment_id=uuid.uuid4(),
        idempotency_key=str(uuid.uuid4()),
        amount_initiated=0,
        amount=0,
        amount_capturable=0,
        amount_received=0,
        application_fee_amount=0,
        capture_method="manual",
        confirmation_method="manual",
        country="US",
        currency="USD",
        status=PaymentIntentStatus(status),
        statement_descriptor="descriptor",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=None,
        cancelled_at=None,
    )


def generate_pgp_payment_intent(status: str) -> PgpPaymentIntent:
    return PgpPaymentIntent(
        id=uuid.uuid4(),
        payment_intent_id=uuid.uuid4(),
        idempotency_key=str(uuid.uuid4()),
        provider="Stripe",
        resource_id=str(uuid.uuid4()),
        status=PgpPaymentIntentStatus(status),
        invoice_resource_id=None,
        charge_resource_id=None,
        payment_method_resource_id=str(uuid.uuid4),
        currency="USD",
        amount=0,
        amount_capturable=0,
        amount_received=0,
        application_fee_amount=0,
        payout_account_id=str(uuid.uuid4()),
        capture_method="manual",
        confirmation_method="manual",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=None,
        cancelled_at=None,
    )
