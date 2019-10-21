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
from app.payin.repository.cart_payment_repo import CartPaymentRepository


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
            app_context=app_context, job_pool=stripe_pool
        )
        await job_instance.run()
        mock_cart_payment_repository.return_value.find_payment_intents_that_require_capture_before_cutoff.assert_called_once()  # type: ignore

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
        async def mock_find_payment_intents_that_require_capture(*args):
            yield payment_intent

        mock_cart_payment_repository.return_value.find_payment_intents_that_require_capture_before_cutoff = (  # type: ignore
            mock_find_payment_intents_that_require_capture
        )
        job_instance = CaptureUncapturedPaymentIntents(
            app_context=app_context, job_pool=stripe_pool
        )
        await job_instance.run()
        mock_cart_payment_processor.return_value.capture_payment.assert_called_once_with(  # type: ignore
            payment_intent
        )


class TestResolveCapturingPaymentIntents:
    @pytest.mark.asyncio
    @patch(
        "app.payin.jobs.CartPaymentRepository",
        return_value=create_autospec(CartPaymentRepository),
    )
    async def test_capture_uncaptured_payment_intents_when_none_exist(
        self,
        mock_cart_payment_repository: CartPaymentRepository,
        app_context: AppContext,
        stripe_pool: JobPool,
    ):
        payment_intent = PaymentIntentFactory(status=IntentStatus.CAPTURING)
        mock_cart_payment_repository.return_value.find_payment_intents_in_capturing.return_value = [  # type: ignore
            payment_intent
        ]
        job_instance = ResolveCapturingPaymentIntents(
            app_context=app_context, job_pool=stripe_pool
        )
        await job_instance.run()
        mock_cart_payment_repository.return_value.update_payment_intent_status.assert_called_once_with(  # type: ignore
            id=payment_intent.id,
            new_status=IntentStatus.REQUIRES_CAPTURE.value,
            previous_status=IntentStatus.CAPTURING.value,
        )
