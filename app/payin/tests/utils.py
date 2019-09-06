from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock
import uuid
from app.payin.core.cart_payment.model import (
    PaymentIntent,
    PgpPaymentIntent,
    CartPayment,
    CartMetadata,
    CartType,
    PaymentCharge,
    PgpPaymentCharge,
)
from app.payin.core.cart_payment.types import IntentStatus, ChargeStatus, CaptureMethod
from app.payin.core.dispute.model import Dispute
from app.payin.repository.dispute_repo import StripeDisputeDbEntity


class FunctionMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(FunctionMock, self).__call__(*args, **kwargs)


class ContextMock(MagicMock):
    async def __aenter__(self, *args, **kwargs):
        pass

    async def __aexit__(self, *args, **kwargs):
        pass


def generate_payment_intent(
    id: uuid.UUID = None,
    cart_payment_id: uuid.UUID = None,
    status: str = "init",
    amount: int = 500,
    capture_method: str = "manual",
    confirmation_method: str = "manual",
    amount_received: Optional[int] = None,
    captured_at: Optional[datetime] = None,
):
    return PaymentIntent(
        id=id if id else uuid.uuid4(),
        cart_payment_id=cart_payment_id if cart_payment_id else uuid.uuid4(),
        idempotency_key=str(uuid.uuid4()),
        amount_initiated=0,
        amount=amount,
        amount_capturable=0,
        amount_received=amount_received,
        application_fee_amount=0,
        capture_method=capture_method,
        confirmation_method=confirmation_method,
        country="US",
        currency="USD",
        status=IntentStatus(status),
        statement_descriptor="descriptor",
        payment_method_id=str(uuid.uuid4()),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=captured_at,
        cancelled_at=None,
    )


def generate_pgp_payment_intent(
    id: uuid.UUID = None,
    payment_intent_id: uuid.UUID = None,
    status: str = "init",
    amount: int = 500,
    capture_method: str = "manual",
    resource_id: str = str(uuid.uuid4()),
    charge_resource_id: str = "charge_resource_id",
) -> PgpPaymentIntent:
    return PgpPaymentIntent(
        id=id if id else uuid.uuid4(),
        payment_intent_id=payment_intent_id if payment_intent_id else uuid.uuid4(),
        idempotency_key=str(uuid.uuid4()),
        provider="stripe",
        resource_id=str(uuid.uuid4()),
        status=IntentStatus(status),
        invoice_resource_id=None,
        charge_resource_id="charge_resource_id",
        payment_method_resource_id=str(uuid.uuid4()),
        customer_resource_id=str(uuid.uuid4()),
        currency="USD",
        amount=amount,
        amount_capturable=0,
        amount_received=0,
        application_fee_amount=0,
        payout_account_id=None,
        capture_method=capture_method,
        confirmation_method="manual",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=None,
        cancelled_at=None,
    )


def generate_cart_payment(
    id: uuid.UUID = None,
    payer_id: uuid.UUID = uuid.uuid4(),
    payment_method_id: uuid.UUID = uuid.uuid4(),
    amount=500,
    capture_method=CaptureMethod.MANUAL.value,
) -> CartPayment:
    return CartPayment(
        id=id if id else uuid.uuid4(),
        amount=amount,
        payer_id=payer_id,
        payment_method_id=payment_method_id,
        capture_method=capture_method,
        cart_metadata=CartMetadata(
            reference_id=0, ct_reference_id=0, type=CartType.ORDER_CART
        ),
        delay_capture=True,
    )


def generate_payment_charge(
    payment_intent_id: uuid.UUID = uuid.uuid4(),
    status: ChargeStatus = ChargeStatus.REQUIRES_CAPTURE,
    amount: int = 700,
    amount_refunded=0,
) -> PaymentCharge:
    return PaymentCharge(
        id=uuid.uuid4(),
        payment_intent_id=payment_intent_id,
        provider="stripe",
        idempotency_key=str(uuid.uuid4()),
        status=status,
        currency="USD",
        amount=amount,
        amount_refunded=amount_refunded,
        application_fee_amount=None,
        payout_account_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=None,
        cancelled_at=None,
    )


def generate_pgp_payment_charge(
    payment_charge_id: uuid.UUID = uuid.uuid4(),
    status: ChargeStatus = ChargeStatus.REQUIRES_CAPTURE,
    amount: int = 700,
    amount_refunded=0,
) -> PgpPaymentCharge:
    return PgpPaymentCharge(
        id=uuid.uuid4(),
        payment_charge_id=payment_charge_id,
        provider="stripe",
        idempotency_key=str(uuid.uuid4()),
        status=status,
        currency="USD",
        amount=amount,
        amount_refunded=amount_refunded,
        application_fee_amount=None,
        payout_account_id=None,
        resource_id="resource_id",
        intent_resource_id="intent_id",
        invoice_resource_id=None,
        payment_method_resource_id="payment_id",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        captured_at=None,
        cancelled_at=None,
    )


def _generate_provider_charge(
    payment_intent: PaymentIntent,
    pgp_payment_intent: PgpPaymentIntent,
    amount_refunded: int = 0,
):
    provider_charge = MagicMock()
    provider_charge.currency = pgp_payment_intent.currency
    provider_charge.amount = pgp_payment_intent.amount
    provider_charge.amount_refunded = amount_refunded
    provider_charge.application_fee_amount = pgp_payment_intent.application_fee_amount
    provider_charge.on_behalf_of = pgp_payment_intent.payout_account_id
    provider_charge.charge_id = str(uuid.uuid4())
    provider_charge.payment_intent = pgp_payment_intent.resource_id
    provider_charge.invoice = str(uuid.uuid4())
    provider_charge.payment_method = str(uuid.uuid4())
    return provider_charge


def generate_provider_charges(
    payment_intent: PaymentIntent,
    pgp_payment_intent: PgpPaymentIntent,
    amount_refunded: int = 0,
):
    charges = MagicMock()
    charges.data = [
        _generate_provider_charge(payment_intent, pgp_payment_intent, amount_refunded)
    ]

    return charges


def generate_dispute() -> Dispute:
    return Dispute(
        id=1,
        stripe_dispute_id="1",
        disputed_at=datetime.now(),
        amount=100,
        fee=10,
        net=110,
        charged_at=datetime.now(),
        reason="subscription_cancelled",
        status="needs_response",
        evidence_due_by=datetime.now(),
        stripe_charge_id=1,
        stripe_card_id=1,
    )


def generate_dispute_db_entity() -> StripeDisputeDbEntity:
    return StripeDisputeDbEntity(
        id=1,
        stripe_dispute_id="1",
        disputed_at=datetime.now(),
        amount=100,
        fee=10,
        net=110,
        charged_at=datetime.now(),
        reason="subscription_cancelled",
        status="needs_response",
        evidence_due_by=datetime.now(),
        stripe_charge_id=1,
        stripe_card_id=1,
    )
