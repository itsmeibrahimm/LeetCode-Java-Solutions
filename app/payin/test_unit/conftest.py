import pytest
from unittest.mock import MagicMock

from app.payin.core.cart_payment.processor import CartPaymentInterface
from app.payin.tests.utils import FunctionMock, ContextMock


@pytest.fixture
def cart_payment_repo():
    """
    Provide a mocked cart_payment repository class.  Functions simply return MagicMocks.
    Tests that require specific behaviors can update mocked functions as needed.

    Returns:
        MagicMock -- Mocked cart payment repo.
    """
    payment_repo = MagicMock()

    # Cart Payment DB Functions
    payment_repo.insert_cart_payment = FunctionMock(return_value=MagicMock())

    # Intent DB Functions
    payment_repo.update_payment_intent_status = FunctionMock(return_value=MagicMock())
    payment_repo.update_pgp_payment_intent = FunctionMock(return_value=MagicMock())
    payment_repo.update_pgp_payment_intent_status = FunctionMock(
        return_value=MagicMock()
    )
    payment_repo.insert_payment_intent_adjustment_history = FunctionMock(
        return_value=MagicMock()
    )
    payment_repo.insert_payment_intent = FunctionMock(return_value=MagicMock())
    payment_repo.insert_pgp_payment_intent = FunctionMock(return_value=MagicMock())
    payment_repo.get_payment_intent_for_idempotency_key = FunctionMock(
        return_value=None
    )

    # Charge DB Functions
    payment_repo.insert_payment_charge = FunctionMock(return_value=MagicMock())
    payment_repo.insert_pgp_payment_charge = FunctionMock(return_value=MagicMock())
    payment_repo.update_payment_charge_status = FunctionMock(return_value=MagicMock())
    payment_repo.update_pgp_payment_charge = FunctionMock(return_value=MagicMock())
    payment_repo.update_pgp_payment_charge_status = FunctionMock(
        return_value=MagicMock()
    )

    # Transaction function
    payment_repo.payment_database_transaction = ContextMock()

    return payment_repo


@pytest.fixture
def stripe_interface():
    """
    Provide a mocked stripe interface.  Functions return a dummy objects, such as a mocked
    PaymentIntent isntance.

    Returns:
        MagicMock -- Stripe instance.
    """
    stripe = MagicMock()

    # Intent functions
    mocked_intent = MagicMock()
    mocked_intent.id = "test_intent_id"
    mocked_intent.status = "succeeded"
    mocked_intent.charges = MagicMock()
    mocked_intent.charges.data = [MagicMock()]

    stripe.create_payment_intent = FunctionMock(return_value=mocked_intent)
    stripe.cancel_payment_intent = FunctionMock(return_value=mocked_intent)
    stripe.capture_payment_intent = FunctionMock(return_value=mocked_intent)

    # Refund functions
    mocked_refund = MagicMock()
    mocked_refund.id = "test_refund"
    mocked_refund.status = "succeeded"
    mocked_refund.amount = 200

    stripe.refund_charge = FunctionMock(return_value=mocked_refund)

    return stripe


@pytest.fixture
def cart_payment_interface(cart_payment_repo, stripe_interface):
    """
    Returns a cart payment interface with a default mocked stripe client and cart payment repository, where
    functions within these provide default (e.g. simple mock) responses.
    """
    cart_payment_interface = CartPaymentInterface(
        app_context=MagicMock(),
        req_context=MagicMock(),
        payment_repo=cart_payment_repo,
        payer_client=MagicMock(),
        payment_method_client=MagicMock(),
    )

    # Lookup functions
    cart_payment_interface._get_required_payment_resource_ids = FunctionMock(
        return_value=("payment_method_id", "customer_id")
    )

    # Stripe functions
    cart_payment_interface.app_context.stripe = stripe_interface

    return cart_payment_interface
