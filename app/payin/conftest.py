import functools
from datetime import datetime, timezone
from uuid import uuid4

import factory
import pytest

from app.commons.types import CountryCode, Currency, PgpCode
from app.payin.core.cart_payment.model import (
    PaymentIntent,
    CartPayment,
    CorrelationIds,
    PgpPaymentIntent,
)
from app.payin.core.cart_payment.types import (
    IntentStatus,
    CaptureMethod,
    LegacyConsumerChargeId,
)
from app.payin.core.payer.model import Payer
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.types import PayerReferenceIdType
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository, InsertPayerInput


@pytest.fixture
async def payment_intent(
    cart_payment_repository: CartPaymentRepository, payer_repository: PayerRepository
):
    payer = PayerFactory()  # type: Payer
    insert_payer_input = InsertPayerInput(
        id=payer.id,
        payer_reference_id=payer.payer_reference_id,
        payer_reference_id_type=payer.payer_reference_id_type,
        country=payer.country,
        created_at=payer.created_at,
        updated_at=payer.updated_at,
    )
    payer_db_entity = await payer_repository.insert_payer(insert_payer_input)
    cart_payment = CartPaymentFactory()  # type: CartPayment
    cart_payment = await cart_payment_repository.insert_cart_payment(
        id=cart_payment.id,
        payer_id=payer_db_entity.id,
        client_description=cart_payment.client_description,
        reference_id=cart_payment.correlation_ids.reference_id,
        reference_type=cart_payment.correlation_ids.reference_type,
        amount_original=100,
        legacy_consumer_id=None,
        amount_total=200,
        delay_capture=False,
        metadata=None,
        legacy_stripe_card_id=1,
        legacy_provider_customer_id="stripe_customer_id",
        legacy_provider_card_id="stripe_card_id",
    )

    payment_method_processor = PaymentMethodProcessor()
    payment_method = await payment_method_processor.create_payment_method(
        pgp_code=PgpCode.STRIPE,
        token="tok_visa",
        payer_id=payer.id,
        set_default=False,
        is_scanned=False,
        is_active=True,
    )

    payment_intent = PaymentIntentFactory(
        status=IntentStatus.REQUIRES_CAPTURE.value, payment_method_id=payment_method.id
    )  # type: PaymentIntent

    return await cart_payment_repository.insert_payment_intent(
        id=payment_intent.id,
        cart_payment_id=cart_payment.id,
        idempotency_key=payment_intent.idempotency_key,
        amount_initiated=payment_intent.amount_initiated,
        amount=payment_intent.amount,
        application_fee_amount=payment_intent.application_fee_amount,
        country=payment_intent.country,
        currency=payment_intent.currency,
        capture_method=payment_intent.capture_method,
        status=payment_intent.status,
        statement_descriptor=payment_intent.statement_descriptor,
        capture_after=datetime(2016, 1, 1),
        payment_method_id=payment_intent.payment_method_id,
        metadata=None,
        legacy_consumer_charge_id=LegacyConsumerChargeId(127683),
    )


# Factories


class PaymentIntentFactory(factory.Factory):
    class Meta:
        model = PaymentIntent

    id = factory.LazyAttribute(lambda o: uuid4())
    cart_payment_id = factory.LazyAttribute(lambda o: str(uuid4()))
    idempotency_key = factory.LazyAttribute(lambda o: str(uuid4()))
    amount_initiated = 100
    amount = 100
    application_fee_amount = 0
    capture_method = CaptureMethod.MANUAL
    country = CountryCode.US
    currency = Currency.USD
    status = IntentStatus.INIT
    statement_descriptor = "Maccas"
    payment_method_id = factory.LazyAttribute(lambda o: str(uuid4()))
    legacy_consumer_charge_id = 0
    created_at = factory.LazyFunction(functools.partial(datetime.now, timezone.utc))
    updated_at = factory.LazyFunction(functools.partial(datetime.now, timezone.utc))
    captured_at = None
    cancelled_at = None


class CartPaymentFactory(factory.Factory):
    class Meta:
        model = CartPayment

    id = factory.LazyAttribute(lambda o: uuid4())
    amount = 100
    payer_id = factory.LazyAttribute(lambda o: uuid4())
    payment_method_id = None
    capture_method = None
    client_description = "Maccas Order"
    metadata = None
    delay_capture = True
    correlation_ids = CorrelationIds(reference_id="1", reference_type="2")


class PayerFactory(factory.Factory):
    class Meta:
        model = Payer

    id = factory.LazyAttribute(lambda o: str(uuid4()))
    payer_reference_id = 11
    payer_reference_id_type = PayerReferenceIdType.DD_DRIVE_STORE_ID.value
    country = CountryCode.US.value
    description = "Xilin"
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class PgpPaymentIntentFactory(factory.Factory):
    class Meta:
        model = PgpPaymentIntent

    id = factory.LazyAttribute(lambda o: str(uuid4()))
    payment_intent_id = factory.LazyAttribute(lambda o: str(uuid4()))
    idempotency_key = factory.LazyAttribute(lambda o: str(uuid4()))
    pgp_code = PgpCode.STRIPE
    resource_id = 1
    status = IntentStatus.REQUIRES_CAPTURE
    invoice_resource_id = "asdf"
    charge_resource_id = "asdf"
    payment_method_resource_id = "asdf"
    customer_resource_id = "asdf"
    capture_method = CaptureMethod.MANUAL.value
    currency = Currency.USD
    amount = 100
    amount_capturable = 100
    amount_received = 100
    application_fee_amount = 100
    payout_account_id = 100
    created_at = datetime
    updated_at = datetime
    captured_at = factory.LazyFunction(datetime.utcnow)
    cancelled_at = factory.LazyFunction(datetime.utcnow)
