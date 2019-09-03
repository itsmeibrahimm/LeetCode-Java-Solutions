from datetime import datetime
from uuid import uuid4

import factory
import pytest

from app.commons.types import CountryCode, CurrencyType
from app.commons.utils.types import PaymentProvider
from app.payin.core.cart_payment.model import (
    PaymentIntent,
    CartMetadata,
    CartPayment,
    PgpPaymentIntent,
)
from app.payin.core.cart_payment.types import (
    IntentStatus,
    CaptureMethod,
    ConfirmationMethod,
    CartType,
)
from app.payin.core.payer.model import Payer
from app.payin.core.payer.types import PayerType
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository, InsertPayerInput


@pytest.fixture
async def payment_intent(
    cart_payment_repository: CartPaymentRepository, payer_repository: PayerRepository
):
    payer = PayerFactory()  # type: Payer
    insert_payer_input = InsertPayerInput(
        id=payer.id,
        payer_type=payer.payer_type,
        country=payer.country,
        dd_payer_id=payer.dd_payer_id,
        created_at=payer.created_at,
        updated_at=payer.updated_at,
    )
    payer_db_entity = await payer_repository.insert_payer(insert_payer_input)
    cart_payment = CartPaymentFactory()  # type: CartPayment
    cart_payment = await cart_payment_repository.insert_cart_payment(
        id=cart_payment.id,
        payer_id=payer_db_entity.id,
        client_description=cart_payment.client_description,
        type=cart_payment.cart_metadata.type,
        reference_id=cart_payment.cart_metadata.reference_id,
        reference_ct_id=cart_payment.cart_metadata.ct_reference_id,
        amount_original=100,
        legacy_consumer_id=None,
        amount_total=200,
        delay_capture=False,
    )

    payment_intent = PaymentIntentFactory(
        status=IntentStatus.REQUIRES_CAPTURE.value
    )  # type: PaymentIntent
    payment_intent = await cart_payment_repository.insert_payment_intent(
        id=payment_intent.id,
        cart_payment_id=cart_payment.id,
        idempotency_key=payment_intent.idempotency_key,
        amount_initiated=payment_intent.amount_initiated,
        amount=payment_intent.amount,
        application_fee_amount=payment_intent.application_fee_amount,
        country=payment_intent.country,
        currency=payment_intent.currency,
        capture_method=payment_intent.capture_method,
        confirmation_method=payment_intent.confirmation_method,
        status=payment_intent.status,
        statement_descriptor=payment_intent.statement_descriptor,
        capture_after=None,
        payment_method_id=payment_intent.payment_method_id,
    )


# Factories


class PaymentIntentFactory(factory.Factory):
    class Meta:
        model = PaymentIntent

    id = factory.LazyAttribute(lambda o: str(uuid4()))
    cart_payment_id = factory.LazyAttribute(lambda o: str(uuid4()))
    idempotency_key = factory.LazyAttribute(lambda o: str(uuid4()))
    amount_initiated = 100
    amount = 100
    amount_capturable = 100
    amount_received = 0
    application_fee_amount = 0
    capture_method = CaptureMethod.MANUAL
    confirmation_method = ConfirmationMethod.MANUAL
    country = CountryCode.US
    currency = CurrencyType.USD
    status = IntentStatus.INIT
    statement_descriptor = "Maccas"
    payment_method_id = "asdf"
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    captured_at = None
    cancelled_at = None


class CartPaymentFactory(factory.Factory):
    class Meta:
        model = CartPayment

    id = factory.LazyAttribute(lambda o: str(uuid4()))
    amount = 100
    payer_id = 1
    payment_method_id = None
    capture_method = None
    client_description = "Maccas Order"
    cart_metadata = CartMetadata(
        reference_id=1, ct_reference_id=2, type=CartType.ORDER_CART
    )


class PayerFactory(factory.Factory):
    class Meta:
        model = Payer

    id = factory.LazyAttribute(lambda o: str(uuid4()))
    payer_type = PayerType.STORE.value
    country = CountryCode.US.value
    dd_payer_id = 11
    description = "Xilin"
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class PgpPaymentIntentFactory(factory.Factory):
    class Meta:
        model = PgpPaymentIntent

    id = factory.LazyAttribute(lambda o: str(uuid4()))
    payment_intent_id = factory.LazyAttribute(lambda o: str(uuid4()))
    idempotency_key = factory.LazyAttribute(lambda o: str(uuid4()))
    provider = PaymentProvider.STRIPE
    resource_id = 1
    status = IntentStatus.REQUIRES_CAPTURE
    invoice_resource_id = "asdf"
    charge_resource_id = "asdf"
    payment_method_resource_id = "asdf"
    customer_resource_id = "asdf"
    capture_method = CaptureMethod.MANUAL.value
    confirmation_method = ConfirmationMethod.MANUAL.value
    currency = CurrencyType.USD
    amount = 100
    amount_capturable = 100
    amount_received = 100
    application_fee_amount = 100
    payout_account_id = 100
    created_at = datetime
    updated_at = datetime
    captured_at = factory.LazyFunction(datetime.utcnow)
    cancelled_at = factory.LazyFunction(datetime.utcnow)
