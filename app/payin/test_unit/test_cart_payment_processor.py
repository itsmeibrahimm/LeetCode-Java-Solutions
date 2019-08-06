import pytest
from unittest.mock import MagicMock
from app.commons.providers.stripe_models import CreatePaymentIntent
import app.payin.core.cart_payment.processor as processor
from app.payin.core.cart_payment.types import PgpPaymentIntentStatus
from app.payin.tests.utils import generate_payment_intent, generate_pgp_payment_intent


class RepoFunctionMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(RepoFunctionMock, self).__call__(*args, **kwargs)


class TestCartPaymentProcessor:
    @pytest.fixture
    def cart_payment_interface(self):
        # TODO set up contexts, payin repo to pass in
        return processor.CartPaymentInterface(
            app_context=MagicMock(), req_context=MagicMock(), payment_repo=MagicMock()
        )

    def test_transform_method_for_stripe(self, cart_payment_interface):
        assert (
            cart_payment_interface._transform_method_for_stripe("auto") == "automatic"
        )
        assert cart_payment_interface._transform_method_for_stripe("manual") == "manual"

    def test_get_provider_capture_method(self, cart_payment_interface):
        intent = generate_payment_intent(capture_method="manual")
        result = cart_payment_interface._get_provider_capture_method(intent)
        assert result == CreatePaymentIntent.CaptureMethod.manual

        intent = generate_payment_intent(capture_method="auto")
        result = cart_payment_interface._get_provider_capture_method(intent)
        assert result == CreatePaymentIntent.CaptureMethod.automatic

    def test_get_provider_confirmation_method(self, cart_payment_interface):
        intent = generate_payment_intent(confirmation_method="manual")
        result = cart_payment_interface._get_provider_confirmation_method(intent)
        assert result == CreatePaymentIntent.ConfirmationMethod.manual

        intent = generate_payment_intent(confirmation_method="auto")
        result = cart_payment_interface._get_provider_confirmation_method(intent)
        assert result == CreatePaymentIntent.ConfirmationMethod.automatic

    def test_get_provider_future_usage(self, cart_payment_interface):
        result = cart_payment_interface._get_provider_future_usage()
        assert result == CreatePaymentIntent.SetupFutureUsage.off_session

    def test_intent_submit_status_evaluation(self, cart_payment_interface):
        intent = generate_payment_intent(status="init")
        assert cart_payment_interface._is_payment_intent_submitted(intent) is False

        intent = generate_payment_intent(status="processing")
        assert cart_payment_interface._is_payment_intent_submitted(intent) is True

    def test_pgp_intent_status_evaluation(self, cart_payment_interface):
        intent = generate_pgp_payment_intent(status="init")
        assert cart_payment_interface._is_pgp_payment_intent_submitted(intent) is False

        intent = generate_pgp_payment_intent(status="processing")
        assert cart_payment_interface._is_pgp_payment_intent_submitted(intent) is True

    def test_get_cart_payment_submission_pgp_intent(self, cart_payment_interface):
        first_intent = generate_pgp_payment_intent("init")
        second_intent = generate_pgp_payment_intent("init")
        pgp_intents = [first_intent, second_intent]
        selected_intent = cart_payment_interface._get_cart_payment_submission_pgp_intent(
            pgp_intents
        )
        assert selected_intent == first_intent

    @pytest.mark.asyncio
    async def test_update_pgp_intent_from_provider(self, cart_payment_interface):
        mock_db_function = RepoFunctionMock()
        cart_payment_interface.payment_repo.update_pgp_payment_intent = mock_db_function

        intent = generate_pgp_payment_intent("init")
        connection = MagicMock()
        provider_payment_response = "ID From Provicer"
        await cart_payment_interface._update_pgp_intent_from_provider(
            connection=connection,
            pgp_intent_id=intent.id,
            status=PgpPaymentIntentStatus.PROCESSING,
            provider_payment_response=provider_payment_response,
        )

        mock_db_function.assert_called_with(
            connection=connection,
            id=intent.id,
            status=PgpPaymentIntentStatus.PROCESSING,
            provider_intent_id=provider_payment_response,
        )

    @pytest.mark.asyncio
    async def test_find_existing_no_matches(self, cart_payment_interface):
        mock_intent_search = RepoFunctionMock(return_value=None)
        cart_payment_interface.payment_repo.get_payment_intent_for_idempotency_key = (
            mock_intent_search
        )
        result = await cart_payment_interface._find_existing(
            payer_id="payer_id", idempotency_key="idempotency_key"
        )
        assert result == (None, None)

    @pytest.mark.asyncio
    async def test_find_existing_with_matches(self, cart_payment_interface):
        # Mock function to find intent
        intent = generate_payment_intent()
        cart_payment_interface.payment_repo.get_payment_intent_for_idempotency_key = RepoFunctionMock(
            return_value=intent
        )

        # Mock function to find cart payment
        cart_payment = MagicMock()
        cart_payment_interface.payment_repo.get_cart_payment_by_id = RepoFunctionMock(
            return_value=cart_payment
        )

        result = await cart_payment_interface._find_existing(
            payer_id="payer_id", idempotency_key="idempotency_key"
        )
        assert result == (cart_payment, intent)
