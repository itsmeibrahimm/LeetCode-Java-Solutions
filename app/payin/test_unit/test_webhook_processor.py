import asyncio
import uuid
from unittest.mock import MagicMock

import pytest
from asynctest import CoroutineMock, mock

from app.commons.types import Currency, PgpCode, CountryCode
from app.payin.core.cart_payment.model import PaymentIntent
from app.payin.core.cart_payment.types import IntentStatus, LegacyConsumerChargeId
from app.payin.core.webhook.model import StripeWebHookEvent
from app.payin.core.webhook.processor import (
    PaymentIntentCreatedHandler,
    PaymentIntentPaymentFailedHandler,
    PaymentIntentSucceededHandler,
)

GLOBAL_PAYMENT_INTENT_ID = uuid.uuid4()


def get_event(id, event_type, status, amount, payment_intent_id, amount_received=0):
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
                "amount_received": amount_received,
            }
        },
        livemode=True,
        pending_webhooks=1,
        type=event_type,
    )


@asyncio.coroutine
def coroutine_created_payment_intent(*args, **kwargs):
    return PaymentIntent(
        id=uuid.uuid4(),
        cart_payment_id=GLOBAL_PAYMENT_INTENT_ID,
        idempotency_key=str(uuid.uuid4()),
        amount_initiated=1000,
        amount=1000,
        application_fee_amount=0,
        capture_method="manual",
        country=CountryCode.US,
        currency=Currency.USD,
        status=IntentStatus.SUCCEEDED,
        pgp_code=PgpCode.STRIPE,
        legacy_consumer_charge_id=LegacyConsumerChargeId(1),
        created_at=1326853478,
        updated_at=1326853480,
        captured_at=None,
        cancelled_at=None,
        resource_id="VALID_RESOURCE_ID",
        capture_after=None,
    )


@asyncio.coroutine
def coroutine_payment_intent_created_failed(*args, **kwargs):
    return PaymentIntent(
        id=uuid.uuid4(),
        cart_payment_id=GLOBAL_PAYMENT_INTENT_ID,
        idempotency_key=str(uuid.uuid4()),
        amount_initiated=1000,
        amount=1000,
        application_fee_amount=0,
        capture_method="manual",
        country=CountryCode.US,
        currency=Currency.USD,
        status=IntentStatus.CANCELLED,
        pgp_code=PgpCode.STRIPE,
        legacy_consumer_charge_id=LegacyConsumerChargeId(1),
        created_at=1326853478,
        updated_at=1326853480,
        captured_at=None,
        cancelled_at=None,
        resource_id="VALID_RESOURCE_ID",
        capture_after=None,
    )


@asyncio.coroutine
def coroutine_payment_intent_succeeded(*args, **kwargs):
    return PaymentIntent(
        id=uuid.uuid4(),
        cart_payment_id=GLOBAL_PAYMENT_INTENT_ID,
        idempotency_key=str(uuid.uuid4()),
        amount_initiated=1000,
        amount=1000,
        application_fee_amount=0,
        capture_method="manual",
        country=CountryCode.US,
        currency=Currency.USD,
        status=IntentStatus.SUCCEEDED,
        pgp_code=PgpCode.STRIPE,
        legacy_consumer_charge_id=LegacyConsumerChargeId(1),
        created_at=1326853478,
        updated_at=1326853480,
        captured_at=132685399,
        cancelled_at=None,
        resource_id="VALID_RESOURCE_ID",
        capture_after=None,
    )


class TestPaymentIntentCreatedHandler:
    @pytest.fixture
    def cart_payment_repository_successful(self):
        cart_payment_repository = MagicMock()
        mock_get_payment_intent_by_id = CoroutineMock()
        mock_get_payment_intent_by_id.side_effect = coroutine_created_payment_intent
        cart_payment_repository.get_payment_intent_by_id_from_primary = (
            mock_get_payment_intent_by_id
        )
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
        cart_payment_repository.get_payment_intent_by_id_from_primary = (
            mock_get_payment_intent_by_id
        )
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
        mock_get_payment_intent_by_id.side_effect = (
            coroutine_payment_intent_created_failed
        )
        cart_payment_repository.get_payment_intent_by_id_from_primary = (
            mock_get_payment_intent_by_id
        )
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
        cart_payment_repository.get_payment_intent_by_id_from_primary = (
            mock_get_payment_intent_by_id
        )
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


class TestPaymentIntentSucceededHandler:
    @pytest.fixture
    def cart_payment_repository_successful(self):
        cart_payment_repository = MagicMock()
        mock_get_payment_intent_by_id = CoroutineMock()
        mock_get_payment_intent_by_id.side_effect = coroutine_payment_intent_succeeded
        cart_payment_repository.get_payment_intent_by_id_from_primary = (
            mock_get_payment_intent_by_id
        )
        return cart_payment_repository

    @pytest.fixture
    def payment_intent_succeeded_successful(self, cart_payment_repository_successful):
        return PaymentIntentSucceededHandler(
            cart_payment_repository=cart_payment_repository_successful, log=MagicMock()
        )

    @pytest.fixture
    def cart_payment_repository_unsuccessful(self):
        cart_payment_repository = MagicMock()
        mock_get_payment_intent_by_id = CoroutineMock()
        mock_get_payment_intent_by_id.side_effect = None
        cart_payment_repository.get_payment_intent_by_id_from_primary = (
            mock_get_payment_intent_by_id
        )
        return cart_payment_repository

    @pytest.fixture
    def payment_intent_succeeded_unsuccessful(
        self, cart_payment_repository_unsuccessful
    ):
        return PaymentIntentPaymentFailedHandler(
            cart_payment_repository=cart_payment_repository_unsuccessful,
            log=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_successful_verification_payment_intent(
        self, payment_intent_succeeded_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.succeeded",
                status="succeeded",
                amount=1000,
                payment_intent_id=GLOBAL_PAYMENT_INTENT_ID,
                amount_received=1000,
            )
            assert event.data.object["metadata"]["payment_intent_id"] is not None
            return_value = await payment_intent_succeeded_successful(
                event=event, country_code="US"
            )
            assert return_value is True

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_not_found(
        self, payment_intent_succeeded_unsuccessful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.succeeded",
                status="cancelled",
                amount=1000,
                payment_intent_id=uuid.uuid4(),
                amount_received=1000,
            )
            assert (
                event.data.object["metadata"]["payment_intent_id"]
                != GLOBAL_PAYMENT_INTENT_ID
            )
            return_value = await payment_intent_succeeded_unsuccessful(
                event=event, country_code="US"
            )
            assert return_value is False

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_no_stripe_id(
        self, payment_intent_succeeded_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id=None,
                event_type="payment_intent.succeeded",
                status="cancelled",
                amount=1000,
                payment_intent_id=uuid.uuid4(),
                amount_received=1000,
            )
            assert event.data.object["id"] is None
            return_value = await payment_intent_succeeded_successful(
                event=event, country_code="US"
            )
            assert return_value is False

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_no_payment_intent_id(
        self, payment_intent_succeeded_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.succeeded",
                status="cancelled",
                amount=1000,
                payment_intent_id=None,
                amount_received=1000,
            )
            assert event.data.object["metadata"]["payment_intent_id"] is None
            return_value = await payment_intent_succeeded_successful(
                event=event, country_code="US"
            )
            assert return_value is False

    @pytest.mark.asyncio
    async def test_unsuccessful_verification_payment_intent_mismatch(
        self, payment_intent_succeeded_successful
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            event = get_event(
                id="tr_00000000000000",
                event_type="payment_intent.succeeded",
                status="successful",
                amount=1000,
                payment_intent_id=uuid.uuid4(),
                amount_received=1200,  # Not equal to 1000 (Actual payment intent received amount)
            )
            return_value = await payment_intent_succeeded_successful(
                event=event, country_code="US"
            )
            assert return_value is False
