import pytest
from unittest.mock import MagicMock
import app.payin.core.cart_payment.processor as processor
from app.payin.tests.utils import generate_payment_intent, generate_pgp_payment_intent


class TestCartPaymentProcessor:
    @pytest.fixture
    def cart_payment_interface(self):
        # TODO set up contexts, payin repo to pass in
        return processor.CartPaymentInterface(
            app_context=MagicMock(), req_context=MagicMock(), payment_repo=MagicMock()
        )

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
