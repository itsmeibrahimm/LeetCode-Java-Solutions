import pytest

from app.commons.types import PgpCode
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.types import IntentStatus, LegacyStripeChargeStatus
from app.payin.core.payer.model import Payer
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.types import PayerReferenceIdType
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.test_integration.processors.cart_payment_test_base import (
    CartPaymentTestBase,
    CartPaymentLegacyTest,
    CartPaymentTest,
    CartPaymentState,
    PaymentIntentState,
    PgpPaymentIntentState,
    StripeChargeState,
)

card_declined = CartPaymentState(
    description="create cart payment with 1000 amount",
    initial_amount=1000,
    amount_delta_update=None,
    expected_amount=1000,
    capture_intents=False,
    delay_capture=False,
    payment_intent_states=[
        PaymentIntentState(
            amount=1000,
            status=IntentStatus.FAILED,
            pgp_payment_intent_state=PgpPaymentIntentState(
                amount=1000,
                amount_capturable=None,
                amount_received=None,
                status=IntentStatus.FAILED,
            ),
            refund_state=None,
            stripe_charge_state=StripeChargeState(
                amount=1000,
                amount_refunded=0,
                status=LegacyStripeChargeStatus.FAILED,
                error_reason="generic_decline",
            ),
        )
    ],
)


class CreateCartPaymentFailureBase(CartPaymentTestBase):
    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    async def _test_cart_payment_creation_error_charge_declined(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method_processor: PaymentMethodProcessor,
    ):
        payment_method, _ = await payment_method_processor.create_payment_method(
            pgp_code=PgpCode.STRIPE,
            token="tok_chargeCustomerFail",
            set_default=True,
            is_scanned=True,
            is_active=True,
            payer_lookup_id=payer.id,
            payer_lookup_id_type=PayerReferenceIdType.PAYER_ID,
        )
        await super()._test_cart_payment_creation_error(
            card_declined,
            cart_payment_processor,
            cart_payment_repository,
            payer,
            payment_method,
        )

        # TODO: Support other failure cases, such as card declined.  Stripe has testing tokens for these cases,
        # but we fail first at attaching the payment method and do not get as far as cart payment creation.


class TestCreateCartPaymentFailure(CreateCartPaymentFailureBase, CartPaymentTest):
    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    async def test_cart_payment_creation_error_charge_declined(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method_processor: PaymentMethodProcessor,
    ):
        await super()._test_cart_payment_creation_error_charge_declined(
            cart_payment_processor=cart_payment_processor,
            cart_payment_repository=cart_payment_repository,
            payer=payer,
            payment_method_processor=payment_method_processor,
        )


class TestCreateLegacyCartPaymentFailure(
    CreateCartPaymentFailureBase, CartPaymentLegacyTest
):
    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    async def test_cart_payment_creation_error_charge_declined(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method_processor: PaymentMethodProcessor,
    ):
        await super()._test_cart_payment_creation_error_charge_declined(
            cart_payment_processor=cart_payment_processor,
            cart_payment_repository=cart_payment_repository,
            payer=payer,
            payment_method_processor=payment_method_processor,
        )
