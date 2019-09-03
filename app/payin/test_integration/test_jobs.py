import pytest
from asynctest import create_autospec, patch

from app.commons.context.app_context import AppContext
from app.payin.conftest import PaymentIntentFactory
from app.payin.jobs import capture_uncaptured_payment_intents
from app.payin.repository.cart_payment_repo import CartPaymentRepository


class TestCaptureUncapturedPaymentIntents:
    @pytest.fixture
    def cart_payment_repository(self):
        return create_autospec(CartPaymentRepository)

    @pytest.mark.asyncio
    async def test_capture_uncaptured_payment_intents_when_none_exist(
        self, app_context: AppContext, cart_payment_repository: CartPaymentRepository
    ):
        await capture_uncaptured_payment_intents(
            app_context=app_context, cart_payment_repo=cart_payment_repository
        )
        cart_payment_repository.find_payment_intents_that_require_capture.assert_called_once()  # type: ignore

    @pytest.mark.asyncio
    @patch("app.payin.jobs.CartPaymentInterface.capture_payment")
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
