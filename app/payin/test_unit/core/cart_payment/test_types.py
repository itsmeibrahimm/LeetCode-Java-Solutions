from app.payin.core.cart_payment.types import IntentStatus


class TestIntentStatus:
    def test_from_str(self):
        assert IntentStatus.from_str("canceled") == IntentStatus.CANCELLED
        assert IntentStatus.from_str("cancelled") == IntentStatus.CANCELLED

    def test_non_terminated_state(self):
        expected_transiting_states = [
            IntentStatus.INIT,
            IntentStatus.CAPTURE_FAILED,
            IntentStatus.REQUIRES_CAPTURE,
            IntentStatus.CAPTURING,
            IntentStatus.PROCESSING,
            IntentStatus.PENDING,
        ]
        assert set(expected_transiting_states) == set(
            IntentStatus.transiting_status()
        ), "unexpected transiting states, did you add new state?"
