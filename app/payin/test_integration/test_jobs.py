import pytest
from asynctest import create_autospec, patch

from app.commons.context.app_context import AppContext
from app.payin.conftest import PaymentIntentFactory
from app.payin.core.cart_payment.types import IntentStatus
from app.payin.jobs import (
    capture_uncaptured_payment_intents,
    resolve_capturing_payment_intents,
)
from app.payin.repository.cart_payment_repo import CartPaymentRepository


@pytest.fixture
def cart_payment_repository():
    return create_autospec(CartPaymentRepository)


class TestCaptureUncapturedPaymentIntents:
    @pytest.mark.asyncio
    async def test_capture_uncaptured_payment_intents_when_none_exist(
        self, app_context: AppContext, cart_payment_repository: CartPaymentRepository
    ):
        await capture_uncaptured_payment_intents(
            app_context=app_context, cart_payment_repo=cart_payment_repository
        )
        cart_payment_repository.find_payment_intents_that_require_capture.assert_called_once()  # type: ignore

    @pytest.mark.asyncio
    @patch("app.payin.jobs.CartPaymentProcessor.capture_payment")
    async def test_capture_uncaptured_payment_intents_when_one_exists(
        self,
        mock_capture_payment,
        app_context: AppContext,
        cart_payment_repository: CartPaymentRepository,
    ):
        payment_intent = PaymentIntentFactory()
        cart_payment_repository.find_payment_intents_that_require_capture.return_value = [  # type: ignore
            payment_intent
        ]
        await capture_uncaptured_payment_intents(
            app_context=app_context, cart_payment_repo=cart_payment_repository
        )
        cart_payment_repository.find_payment_intents_that_require_capture.assert_called_once()  # type: ignore
        mock_capture_payment.assert_called_once_with(payment_intent)  # type: ignore


class TestResolveCapturingPaymentIntents:
    @pytest.mark.asyncio
    async def test_capture_uncaptured_payment_intents_when_none_exist(
        self, app_context: AppContext, cart_payment_repository: CartPaymentRepository
    ):
        payment_intent = PaymentIntentFactory(status=IntentStatus.CAPTURING)
        cart_payment_repository.find_payment_intents_in_capturing.return_value = [  # type: ignore
            payment_intent
        ]
        await resolve_capturing_payment_intents(
            app_context=app_context, cart_payment_repo=cart_payment_repository
        )
        cart_payment_repository.update_payment_intent_status.assert_called_once_with(  # type: ignore
            id=payment_intent.id,
            new_status=IntentStatus.REQUIRES_CAPTURE.value,
            previous_status=IntentStatus.CAPTURING.value,
        )
