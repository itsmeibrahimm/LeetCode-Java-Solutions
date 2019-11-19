from datetime import datetime
from typing import cast
from uuid import uuid4, UUID

import pytest
from starlette.testclient import TestClient

from app.commons.context.app_context import AppContext
from app.commons.types import CountryCode, PgpCode
from app.payin.core.cart_payment.model import PaymentIntent
from app.payin.core.cart_payment.types import (
    CaptureMethod,
    IntentStatus,
    LegacyConsumerChargeId,
)
from app.payin.core.payer.model import Payer
from app.payin.core.payer.types import PayerType
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository, InsertPayerInput
from app.payin.repository.payment_method_repo import (
    PaymentMethodRepository,
    InsertPgpPaymentMethodInput,
    InsertStripeCardInput,
)


@pytest.fixture
def cart_payment_repository(app_context: AppContext) -> CartPaymentRepository:
    return CartPaymentRepository(app_context)


@pytest.fixture
def payer_repository(app_context: AppContext) -> PayerRepository:
    return PayerRepository(app_context)


@pytest.fixture
def payment_method_repository(app_context: AppContext) -> PaymentMethodRepository:
    return PaymentMethodRepository(app_context)


@pytest.fixture
async def payer(payer_repository: PayerRepository):
    insert_payer_input = InsertPayerInput(
        id=uuid4(), payer_type=PayerType.STORE, country=CountryCode.US
    )
    return await payer_repository.insert_payer(insert_payer_input)


@pytest.fixture
async def payment_method(payer, payment_method_repository: PaymentMethodRepository):
    insert_payment_method = InsertPgpPaymentMethodInput(
        id=uuid4(),
        pgp_code=PgpCode.STRIPE,
        pgp_resource_id=str(uuid4()),
        payer_id=payer.id,
    )
    insert_stripe_card = InsertStripeCardInput(
        stripe_id=insert_payment_method.pgp_resource_id,
        fingerprint="fingerprint",
        last4="1500",
        dynamic_last4="1500",
        exp_month="9",
        exp_year="2024",
        type="mastercard",
        active=True,
    )
    insert_pm_result = await payment_method_repository.insert_pgp_payment_method(
        insert_payment_method
    )
    await payment_method_repository.insert_stripe_card(insert_stripe_card)
    yield insert_pm_result


@pytest.fixture
async def cart_payment(cart_payment_repository: CartPaymentRepository, payer: Payer):
    return await cart_payment_repository.insert_cart_payment(
        id=uuid4(),
        payer_id=cast(UUID, payer.id),
        amount_original=99,
        amount_total=100,
        client_description=None,
        reference_id="99",
        reference_type="88",
        delay_capture=False,
        metadata=None,
        legacy_consumer_id=1,
        legacy_stripe_card_id=1,
        legacy_provider_customer_id="stripe_customer_id",
        legacy_provider_card_id="stripe_card_id",
    )


async def create_payment_intent_object(
    cart_payment_repository: CartPaymentRepository,
    payer,
    payment_method,
    payment_intent__capture_after,
):
    cart_payment_id = uuid4()
    await cart_payment_repository.insert_cart_payment(
        id=cart_payment_id,
        payer_id=payer.id,
        amount_original=99,
        amount_total=100,
        client_description=None,
        reference_id="99",
        reference_type="88",
        legacy_consumer_id=None,
        delay_capture=False,
        metadata=None,
        legacy_stripe_card_id=1,
        legacy_provider_customer_id="stripe_customer_id",
        legacy_provider_card_id="stripe_card_id",
    )

    return await cart_payment_repository.insert_payment_intent(
        id=uuid4(),
        cart_payment_id=cart_payment_id,
        idempotency_key=f"ik_{uuid4()}",
        amount_initiated=100,
        amount=200,
        application_fee_amount=100,
        country=CountryCode.US,
        currency="USD",
        capture_method=CaptureMethod.MANUAL,
        status=IntentStatus.REQUIRES_CAPTURE,
        statement_descriptor=None,
        capture_after=payment_intent__capture_after,
        payment_method_id=payment_method.id,
        metadata={"is_first_order": True},
        legacy_consumer_charge_id=LegacyConsumerChargeId(11),
    )


@pytest.fixture
def payment_intent__capture_after() -> datetime:
    """
    Use to override the capture_after of payment_intent
    :return:
    """
    return datetime(2019, 1, 1)


@pytest.fixture
async def payment_intent(
    cart_payment_repository: CartPaymentRepository,
    payer,
    payment_method,
    payment_intent__capture_after: datetime,
):
    yield await create_payment_intent_object(
        cart_payment_repository, payer, payment_method, payment_intent__capture_after
    )


class TestPaymentIntentCreatedWebhook:
    def test_handle_payment_intent_create_webhook(
        self, client: TestClient, payment_intent: PaymentIntent
    ):
        response = client.post(
            "/payin/api/v1/webhook/us",
            json={
                "created": 1326853478,
                "id": "evt_00000000000000",
                "type": "payment_intent.created",
                "object": "event",
                "api_version": "2019-05-16",
                "data": {
                    "object": {
                        "id": "tr_00000000000000",
                        "metadata": {"payment_intent_id": str(payment_intent.id)},
                    }
                },
                "livemode": True,
                "pending_webhooks": 1,
            },
        )
        assert response.status_code == 200


class TestPaymentIntentFailedWebhook:
    def test_handle_payment_intent_failed_webhook(
        self, client: TestClient, payment_intent: PaymentIntent
    ):
        response = client.post(
            "/payin/api/v1/webhook/us",
            json={
                "created": 1326853478,
                "id": "evt_00000000000000",
                "type": "payment_intent.payment_failed",
                "object": "event",
                "api_version": "2019-05-16",
                "data": {
                    "object": {
                        "id": "tr_00000000000000",
                        "metadata": {"payment_intent_id": str(payment_intent.id)},
                    }
                },
                "livemode": True,
                "pending_webhooks": 1,
            },
        )
        assert response.status_code == 200
