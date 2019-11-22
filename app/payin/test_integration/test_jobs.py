from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from asynctest import create_autospec, patch

from app.commons.context.app_context import AppContext
from app.commons.jobs.pool import JobPool
from app.payin.conftest import PaymentIntentFactory
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.types import IntentStatus
from app.payin.jobs import (
    CaptureUncapturedPaymentIntents,
    ResolveCapturingPaymentIntents,
)
from app.payin.repository.cart_payment_repo import (
    CartPaymentRepository,
    UpdatePaymentIntentStatusWhereInput,
)


@pytest.fixture
def cart_payment_repository():
    return create_autospec(CartPaymentRepository)


@pytest.fixture
def stripe_pool() -> JobPool:
    return JobPool(name="stripe")


class TestCaptureUncapturedPaymentIntents:
    @pytest.mark.asyncio
    @patch(
        "app.payin.jobs.CartPaymentRepository",
        return_value=create_autospec(CartPaymentRepository),
    )
    async def test_capture_uncaptured_payment_intents_when_none_exist(
        self,
        mock_cart_payment_repository: CartPaymentRepository,
        app_context: AppContext,
        cart_payment_repository: CartPaymentRepository,
        stripe_pool: JobPool,
    ):
        job_instance = CaptureUncapturedPaymentIntents(
            app_context=app_context,
            job_pool=stripe_pool,
            problematic_capture_delay=timedelta(days=1),
            statsd_client=MagicMock(),
        )
        await job_instance.run()
        mock_cart_payment_repository.return_value.find_payment_intents_that_require_capture.assert_called_once()  # type: ignore

    @pytest.mark.asyncio
    @patch(
        "app.payin.jobs.CartPaymentRepository",
        return_value=create_autospec(CartPaymentRepository),
    )
    @patch(
        "app.payin.jobs.CartPaymentProcessor",
        return_value=create_autospec(CartPaymentProcessor),
    )
    async def test_capture_uncaptured_payment_intents_when_one_exists(
        self,
        mock_cart_payment_processor: CartPaymentProcessor,
        mock_cart_payment_repository: CartPaymentRepository,
        app_context: AppContext,
        stripe_pool: JobPool,
    ):
        payment_intent = PaymentIntentFactory()

        # this is super ugly. can we accomplish the same thing with asynctest?
        async def mock_find_payment_intents_that_require_capture(*args, **kwargs):
            yield payment_intent

        mock_cart_payment_repository.return_value.find_payment_intents_that_require_capture = (  # type: ignore
            mock_find_payment_intents_that_require_capture
        )
        job_instance = CaptureUncapturedPaymentIntents(
            app_context=app_context,
            job_pool=stripe_pool,
            problematic_capture_delay=timedelta(days=1),
            statsd_client=MagicMock(),
        )
        await job_instance.run()
        await stripe_pool.join()
        mock_cart_payment_processor.return_value.capture_payment.assert_called_once_with(  # type: ignore
            payment_intent
        )


class TestResolveCapturingPaymentIntents:
    @pytest.mark.asyncio
    @patch(
        "app.payin.jobs.CartPaymentRepository",
        return_value=create_autospec(CartPaymentRepository),
    )
    async def test_resolve_payment_intent_to_requires_capture(
        self,
        mock_cart_payment_repository: CartPaymentRepository,
        app_context: AppContext,
        stripe_pool: JobPool,
    ):
        payment_intent = PaymentIntentFactory(
            status=IntentStatus.CAPTURING,
            updated_at=datetime.now(timezone.utc) - timedelta(hours=5),
            capture_after=datetime.now(timezone.utc) - timedelta(hours=5),
        )

        payment_intent_right_on_capture = PaymentIntentFactory(
            status=IntentStatus.CAPTURING,
            capture_after=datetime.now(timezone.utc) - timedelta(minutes=30),
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )

        mock_cart_payment_repository.return_value.find_payment_intents_in_capturing.return_value = [  # type: ignore
            payment_intent,
            payment_intent_right_on_capture,
        ]

        job_instance = ResolveCapturingPaymentIntents(
            app_context=app_context,
            job_pool=stripe_pool,
            problematic_capture_delay=timedelta(days=1),
            statsd_client=MagicMock(),
        )
        await job_instance.run()
        await stripe_pool.join()
        mock_cart_payment_repository.return_value.update_payment_intent_status.assert_called_once()  # type: ignore
        args, kwargs = (
            mock_cart_payment_repository.return_value.update_payment_intent_status.call_args  # type: ignore
        )
        assert "update_payment_intent_status_where_input" in kwargs
        assert (
            kwargs["update_payment_intent_status_where_input"].previous_status
            == IntentStatus.CAPTURING
        )
        assert (
            kwargs["update_payment_intent_status_where_input"].id == payment_intent.id
        )
        assert "update_payment_intent_status_set_input" in kwargs
        assert (
            kwargs["update_payment_intent_status_set_input"].status
            == IntentStatus.REQUIRES_CAPTURE
        )

    @pytest.mark.asyncio
    @patch(
        "app.payin.jobs.CartPaymentRepository",
        return_value=create_autospec(CartPaymentRepository),
    )
    async def test_resolve_payment_intent_to_capture_failed(
        self,
        mock_cart_payment_repository: CartPaymentRepository,
        app_context: AppContext,
        stripe_pool: JobPool,
    ):
        payment_intent = PaymentIntentFactory(
            status=IntentStatus.CAPTURING,
            capture_after=datetime.now(timezone.utc) - timedelta(days=5),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )

        payment_intent_right_on_capture = PaymentIntentFactory(
            status=IntentStatus.CAPTURING,
            capture_after=datetime.now(timezone.utc) - timedelta(minutes=30),
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )

        mock_cart_payment_repository.return_value.find_payment_intents_in_capturing.return_value = [  # type: ignore
            payment_intent,
            payment_intent_right_on_capture,
        ]

        job_instance = ResolveCapturingPaymentIntents(
            app_context=app_context,
            job_pool=stripe_pool,
            problematic_capture_delay=timedelta(days=1),
            statsd_client=MagicMock(),
        )
        await job_instance.run()
        await stripe_pool.join()
        mock_cart_payment_repository.return_value.update_payment_intent_status.assert_called_once()  # type: ignore
        args, kwargs = (
            mock_cart_payment_repository.return_value.update_payment_intent_status.call_args  # type: ignore
        )
        update_payment_intent_status_where_input = kwargs[
            "update_payment_intent_status_where_input"
        ]
        update_payment_intent_status_where_request = UpdatePaymentIntentStatusWhereInput(
            id=payment_intent.id, previous_status=IntentStatus.CAPTURING.value
        )
        assert (
            update_payment_intent_status_where_input
            == update_payment_intent_status_where_request
        )
        assert (
            IntentStatus.CAPTURE_FAILED.value
            == kwargs["update_payment_intent_status_set_input"].status
        )
        assert isinstance(
            kwargs["update_payment_intent_status_set_input"].updated_at, datetime
        )
