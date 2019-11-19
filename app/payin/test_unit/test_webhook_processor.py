import asyncio
import uuid
from unittest.mock import MagicMock

import pytest
from asynctest import CoroutineMock, mock

from app.commons.types import Currency, PgpCode
from app.payin.core.cart_payment.model import PaymentIntent
from app.payin.core.cart_payment.types import IntentStatus, LegacyConsumerChargeId
from app.payin.core.webhook.model import StripeWebHookEvent
from app.payin.core.webhook.processor import (
    PaymentIntentCreatedHandler,
    PaymentIntentPaymentFailedHandler,
)

GLOBAL_PAYMENT_INTENT_ID = uuid.uuid4()


def get_event(id, event_type, status, amount, payment_intent_id):
    return StripeWebHookEvent(
        id="evt_00000000000000",
        object="event",
        api_version="2019-05-16",
        created=1326853478,
        data={
            "object": {
                "id": id,
                "metadata": {"payment_intent_id": payment_intent_id},
                "status": status,
                "amount": amount,
                "application_fee_amount": 0,
            }
        },
        livemode=True,
        pending_webhooks=1,
        type=event_type,
    )


@asyncio.coroutine
def coroutine_successful_payment_intent(*args, **kwargs):
    return PaymentIntent(
        id=uuid.uuid4(),
        cart_payment_id=GLOBAL_PAYMENT_INTENT_ID,
        idempotency_key=str(uuid.uuid4()),
        amount_initiated=1000,
        pgp_code=PgpCode.STRIPE,
        resource_id="VALID_RESOURCE_ID",
        status=IntentStatus.SUCCEEDED,
        invoice_resource_id="VALID_INVOICE_RESOURCE_ID",
        charge_resource_id="VALID_CHARGE_RESOURCE_ID",
        payment_method_resource_id="VALID_PAYMENT_METHOD_RESOURCE_ID",
        customer_resource_id="VALID_CUSTOMER_RESOURCE_ID",
        currency=Currency.USD,
        amount=1000,
        amount_capturable=0,
        amount_received=0,
        application_fee_amount=0,
        payout_account_id="VALID_PAYOUT_ACCOUNT_ID",
        capture_method="manual",
        country="US",
        legacy_consumer_charge_id=LegacyConsumerChargeId(1),
        created_at=1326853478,
        updated_at=1326853480,
        captured_at=None,
        cancelled_at=None,
    )


@asyncio.coroutine
def coroutine_failed_payment_intent(*args, **kwargs):
    return PaymentIntent(
        id=uuid.uuid4(),
        cart_payment_id=GLOBAL_PAYMENT_INTENT_ID,
        idempotency_key=str(uuid.uuid4()),
        amount_initiated=1000,
        pgp_code=PgpCode.STRIPE,
        resource_id="VALID_RESOURCE_ID",
        status=IntentStatus.CANCELLED,
        invoice_resource_id="VALID_INVOICE_RESOURCE_ID",
        charge_resource_id="VALID_CHARGE_RESOURCE_ID",
        payment_method_resource_id="VALID_PAYMENT_METHOD_RESOURCE_ID",
        customer_resource_id="VALID_CUSTOMER_RESOURCE_ID",
        currency=Currency.USD,
        amount=1000,
        amount_capturable=0,
        amount_received=0,
        application_fee_amount=0,
        payout_account_id="VALID_PAYOUT_ACCOUNT_ID",
        capture_method="manual",
        country="US",
        legacy_consumer_charge_id=LegacyConsumerChargeId(1),
        created_at=1326853478,
        updated_at=1326853480,
        captured_at=None,
        cancelled_at=None,
    )


class TestPaymentIntentCreatedHandler:
    @pytest.fixture
    def cart_payment_repository_successful(self):
        cart_payment_repository = MagicMock()
        mock_get_payment_intent_by_id = CoroutineMock()
        mock_get_payment_intent_by_id.side_effect = coroutine_successful_payment_intent
        cart_payment_repository.get_payment_intent_by_id = mock_get_payment_intent_by_id
        return cart_payment_repository

    @pytest.fixture
    def payment_intent_created_successful(self, cart_payment_repository_successful):
        return PaymentIntentCreatedHandler(
            cart_payment_repository=cart_payment_repository_successful, log=MagicMock()
        )

    @pytest.fixture
    def cart_payment_repository_unsuccessful(self):
        cart_payment_repository = MagicMock()
        mock_get_payment_intent_by_id = CoroutineMock()
        mock_get_payment_intent_by_id.side_effect = None
        cart_payment_repository.get_payment_intent_by_id = mock_get_payment_intent_by_id
        return cart_payment_repository

    @pytest.fixture
    def payment_intent_created_unsuccessful(self, cart_payment_repository_unsuccessful):
        return PaymentIntentCreatedHandler(
            cart_payment_repository=cart_payment_repository_unsuccessful,
            log=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_successful_verification_payment_intent(
        self, payment_intent_created_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.created",
                status="succeeded",
                amount=1000,
                payment_intent_id=GLOBAL_PAYMENT_INTENT_ID,
            )
            assert event.data.object["metadata"]["payment_intent_id"] is not None
            return_value = await payment_intent_created_successful(
                event=event, country_code="US"
            )
            assert return_value is True

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_not_found(
        self, payment_intent_created_unsuccessful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.created",
                status="succeeded",
                amount=1000,
                payment_intent_id=uuid.uuid4(),
            )
            assert (
                event.data.object["metadata"]["payment_intent_id"]
                != GLOBAL_PAYMENT_INTENT_ID
            )
            return_value = await payment_intent_created_unsuccessful(
                event=event, country_code="US"
            )
            assert return_value is False

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_no_stripe_id(
        self, payment_intent_created_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id=None,
                event_type="payment_intent.created",
                status="succeeded",
                amount=1000,
                payment_intent_id=None,
            )
            assert event.data.object["id"] is None
            return_value = await payment_intent_created_successful(
                event=event, country_code="US"
            )
            assert return_value is False

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_no_payment_intent_id(
        self, payment_intent_created_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id=None,
                event_type="payment_intent.created",
                status="succeeded",
                amount=1000,
                payment_intent_id=None,
            )
            assert event.data.object["metadata"]["payment_intent_id"] is None
            return_value = await payment_intent_created_successful(
                event=event, country_code="US"
            )
            assert return_value is False

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_mismatch(
        self, payment_intent_created_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id=None,
                event_type="payment_intent.created",
                status="succeeded",
                amount=1200,  # Not equal to 1000 (Actual payment intent amount)
                payment_intent_id=None,
            )
            return_value = await payment_intent_created_successful(
                event=event, country_code="US"
            )
            assert return_value is False


class TestPaymentIntentFailedHandler:
    @pytest.fixture
    def cart_payment_repository_successful(self):
        cart_payment_repository = MagicMock()
        mock_get_payment_intent_by_id = CoroutineMock()
        mock_get_payment_intent_by_id.side_effect = coroutine_failed_payment_intent
        cart_payment_repository.get_payment_intent_by_id = mock_get_payment_intent_by_id
        return cart_payment_repository

    @pytest.fixture
    def payment_intent_failed_successful(self, cart_payment_repository_successful):
        return PaymentIntentPaymentFailedHandler(
            cart_payment_repository=cart_payment_repository_successful, log=MagicMock()
        )

    @pytest.fixture
    def cart_payment_repository_unsuccessful(self):
        cart_payment_repository = MagicMock()
        mock_get_payment_intent_by_id = CoroutineMock()
        mock_get_payment_intent_by_id.side_effect = None
        cart_payment_repository.get_payment_intent_by_id = mock_get_payment_intent_by_id
        return cart_payment_repository

    @pytest.fixture
    def payment_intent_failed_unsuccessful(self, cart_payment_repository_unsuccessful):
        return PaymentIntentPaymentFailedHandler(
            cart_payment_repository=cart_payment_repository_unsuccessful,
            log=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_successful_verification_payment_intent(
        self, payment_intent_failed_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.payment_failed",
                status="cancelled",
                amount=1000,
                payment_intent_id=GLOBAL_PAYMENT_INTENT_ID,
            )
            assert event.data.object["metadata"]["payment_intent_id"] is not None
            return_value = await payment_intent_failed_successful(
                event=event, country_code="US"
            )
            assert return_value is True

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_not_found(
        self, payment_intent_failed_unsuccessful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.payment_failed",
                status="cancelled",
                amount=1000,
                payment_intent_id=uuid.uuid4(),
            )
            assert (
                event.data.object["metadata"]["payment_intent_id"]
                != GLOBAL_PAYMENT_INTENT_ID
            )
            return_value = await payment_intent_failed_unsuccessful(
                event=event, country_code="US"
            )
            assert return_value is False

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_no_stripe_id(
        self, payment_intent_failed_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id=None,
                event_type="payment_intent.payment_failed",
                status="cancelled",
                amount=1000,
                payment_intent_id=uuid.uuid4(),
            )
            assert event.data.object["id"] is None
            return_value = await payment_intent_failed_successful(
                event=event, country_code="US"
            )
            assert return_value is False

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_no_payment_intent_id(
        self, payment_intent_failed_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.payment_failed",
                status="cancelled",
                amount=1000,
                payment_intent_id=None,
            )
            assert event.data.object["metadata"]["payment_intent_id"] is None
            return_value = await payment_intent_failed_successful(
                event=event, country_code="US"
            )
            assert return_value is False

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_mismatch(
        self, payment_intent_failed_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.payment_failed",
                status="cancelled",
                amount=1200,  # Not equal to 1000 (Actual payment intent amount)
                payment_intent_id=uuid.uuid4(),
            )
            return_value = await payment_intent_failed_successful(
                event=event, country_code="US"
            )
            assert return_value is False
