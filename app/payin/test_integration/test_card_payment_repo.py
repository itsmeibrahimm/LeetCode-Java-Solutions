from uuid import uuid4

import pytest

from app.commons.types import CountryCode
from app.payin.core.cart_payment.types import (
    IntentStatus,
    CaptureMethod,
    ConfirmationMethod,
    CartType,
)
from app.payin.core.payer.types import PayerType
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository, InsertPayerInput


@pytest.fixture
async def payment_intent(
    payer_repository: PayerRepository, cart_payment_repository: CartPaymentRepository
):
    connection = await cart_payment_repository.get_payment_database_connection()

    insert_payer_input = InsertPayerInput(
        id=str(uuid4()), payer_type=PayerType.STORE, country=CountryCode.US
    )

    payer = await payer_repository.insert_payer(insert_payer_input)

    cart_payment_id = uuid4()

    await cart_payment_repository.insert_cart_payment(
        connection=connection,
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
        connection=connection,
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
    async def test_find_uncaptured_payment_intents_when_none_exist(
        self, cart_payment_repository
    ):
        uncaptured_payment_intents = (
            await cart_payment_repository.find_uncaptured_payment_intents()
        )
        assert uncaptured_payment_intents == []

    @pytest.mark.asyncio
    async def test_find_uncaptured_payment_intents_when_one_exists(
        self, cart_payment_repository, payment_intent
    ):
        uncaptured_payment_intents = (
            await cart_payment_repository.find_uncaptured_payment_intents()
        )
        uncaptured_payment_intent_ids = [pi.id for pi in uncaptured_payment_intents]
        assert uncaptured_payment_intent_ids == [payment_intent.id]
