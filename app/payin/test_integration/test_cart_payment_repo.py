from uuid import uuid4

import pytest

from app.commons.types import CountryCode
from app.payin.core.cart_payment.model import (
    CartPayment,
    PaymentIntentAdjustmentHistory,
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
async def payer(payer_repository: PayerRepository):
    insert_payer_input = InsertPayerInput(
        id=str(uuid4()), payer_type=PayerType.STORE, country=CountryCode.US
    )
    yield await payer_repository.insert_payer(insert_payer_input)


@pytest.fixture
async def cart_payment(cart_payment_repository: CartPaymentRepository, payer: Payer):
    yield await cart_payment_repository.insert_cart_payment(
        id=uuid4(),
        payer_id=payer.id,
        type=CartType.ORDER_CART,
        amount_original=99,
        amount_total=100,
        client_description=None,
        reference_id=99,
        reference_ct_id=88,
        legacy_consumer_id=None,
    )


@pytest.fixture
async def payment_intent(cart_payment_repository: CartPaymentRepository, payer: Payer):
    cart_payment_id = uuid4()
    await cart_payment_repository.insert_cart_payment(
        id=cart_payment_id,
        payer_id=payer.id,
        type=CartType.ORDER_CART,
        amount_original=99,
        amount_total=100,
        client_description=None,
        reference_id=99,
        reference_ct_id=88,
        legacy_consumer_id=None,
    )

    payment_intent = await cart_payment_repository.insert_payment_intent(
        id=uuid4(),
        cart_payment_id=cart_payment_id,
        idempotency_key=f"ik_{uuid4()}",
        amount_initiated=100,
        amount=200,
        application_fee_amount=100,
        country=CountryCode.US,
        currency="USD",
        capture_method=CaptureMethod.MANUAL,
        confirmation_method=ConfirmationMethod.MANUAL,
        status=IntentStatus.REQUIRES_CAPTURE,
        statement_descriptor=None,
    )
    yield payment_intent


class TestPaymentIntent:
    @pytest.mark.asyncio
    @pytest.mark.skip("fix this to not relying on forcerollback")
    async def test_find_uncaptured_payment_intents_when_none_exist(
        self, cart_payment_repository: CartPaymentRepository
    ):
        uncaptured_payment_intents = (
            await cart_payment_repository.find_uncaptured_payment_intents()
        )
        assert uncaptured_payment_intents == []

    @pytest.mark.asyncio
    @pytest.mark.skip("fix this to not relying on forcerollback")
    async def test_find_uncaptured_payment_intents_when_one_exists(
        self, cart_payment_repository: CartPaymentRepository, payment_intent
    ):
        uncaptured_payment_intents = (
            await cart_payment_repository.find_uncaptured_payment_intents()
        )
        uncaptured_payment_intent_ids = [pi.id for pi in uncaptured_payment_intents]
        assert uncaptured_payment_intent_ids == [payment_intent.id]


class TestPaymentIntentAdjustmentHistory:
    @pytest.mark.asyncio
    async def test_insert_history(
        self, cart_payment_repository: CartPaymentRepository, cart_payment: CartPayment
    ):
        payment_intent = await cart_payment_repository.insert_payment_intent(
            id=uuid4(),
            cart_payment_id=cart_payment.id,
            idempotency_key=f"ik_{uuid4()}",
            amount_initiated=100,
            amount=200,
            application_fee_amount=100,
            country=CountryCode.US,
            currency="USD",
            capture_method=CaptureMethod.MANUAL,
            confirmation_method=ConfirmationMethod.MANUAL,
            status=IntentStatus.REQUIRES_CAPTURE,
            statement_descriptor=None,
        )

        id = uuid4()
        result = await cart_payment_repository.insert_payment_intent_adjustment_history(
            id=id,
            payer_id=cart_payment.payer_id,
            payment_intent_id=payment_intent.id,
            amount=payment_intent.amount + 100,
            amount_original=payment_intent.amount,
            amount_delta=100,
            currency=payment_intent.currency,
        )

        expected_adjustment = PaymentIntentAdjustmentHistory(
            id=id,
            payer_id=cart_payment.payer_id,
            payment_intent_id=payment_intent.id,
            amount=payment_intent.amount + 100,
            amount_original=payment_intent.amount,
            amount_delta=100,
            currency=payment_intent.currency,
            created_at=result.created_at,  # Do not know exact created_at ahead of time
        )

        assert result == expected_adjustment
