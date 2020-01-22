from datetime import datetime, timezone

import pytest
from asynctest import mock
from stripe.error import InvalidRequestError

from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.types import (
    IntentStatus,
    LegacyStripeChargeStatus,
    RefundStatus,
)
from app.payin.core.payer.model import Payer
from app.payin.core.payment_method.model import PaymentMethod
from app.payin.repository.cart_payment_repo import (
    CartPaymentRepository,
    UpdatePaymentIntentWhereInput,
    UpdatePaymentIntentSetInput,
)
from app.payin.test_integration.processors.cart_payment_test_base import (
    CartPaymentLegacyTest,
    CartPaymentState,
    PaymentIntentState,
    PgpPaymentIntentState,
    RefundReason,
    RefundState,
    StripeChargeState,
)


class TestSubmitSmallAmountIntentCaptureLegacy(CartPaymentLegacyTest):
    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    async def test_capture_succeeded_but_fail_before_refund_then_retry(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):

        # clean up all dirty payment intents from other tests
        dirty_payment_intents = cart_payment_repository.find_payment_intents_that_require_capture(
            capturable_before=datetime(year=3000, month=12, day=1),
            earliest_capture_after=datetime(year=1972, month=1, day=1),
        )
        now = datetime.now(timezone.utc)
        async for intent in dirty_payment_intents:
            await cart_payment_repository.update_payment_intent(
                update_payment_intent_status_where_input=UpdatePaymentIntentWhereInput(
                    id=intent.id, previous_status=intent.status
                ),
                update_payment_intent_status_set_input=UpdatePaymentIntentSetInput(
                    status=IntentStatus.FAILED, updated_at=now
                ),
            )

        # 1 Setup initial cart payment with delay capture
        initial_state = CartPaymentState(
            description="create cart payment with 1000 amount",
            initial_amount=1000,
            amount_delta_update=None,
            expected_amount=1000,
            capture_intents=False,
            delay_capture=True,
            payment_intent_states=[
                PaymentIntentState(
                    amount=1000,
                    status=IntentStatus.REQUIRES_CAPTURE,
                    pgp_payment_intent_state=PgpPaymentIntentState(
                        amount=1000,
                        amount_capturable=1000,
                        amount_received=0,
                        status=IntentStatus.REQUIRES_CAPTURE,
                    ),
                    refund_state=None,
                    stripe_charge_state=StripeChargeState(
                        amount=1000,
                        amount_refunded=0,
                        status=LegacyStripeChargeStatus.SUCCEEDED,
                        error_reason="",
                    ),
                )
            ],
        )

        cart_payment = await self._test_cart_payment_state_transition(
            [initial_state],
            cart_payment_processor=cart_payment_processor,
            cart_payment_repository=cart_payment_repository,
            payer=payer,
            payment_method=payment_method,
        )

        initial_payment_intents = await cart_payment_repository.get_payment_intents_by_cart_payment_id_from_primary(
            cart_payment_id=cart_payment.id
        )
        initial_payment_intent = initial_payment_intents[0]
        consumer_charge_id = initial_payment_intent.legacy_consumer_charge_id

        # 2 Adjust so that the remaining amount to capture is below threshold
        lower_amount = CartPaymentState(
            description="[partial refund] adjust cart payment with -999 amount",
            initial_amount=1000,
            amount_delta_update=-999,
            expected_amount=1,
            capture_intents=False,
            delay_capture=True,
            payment_intent_states=[
                PaymentIntentState(
                    amount=1,
                    status=IntentStatus.REQUIRES_CAPTURE,
                    pgp_payment_intent_state=PgpPaymentIntentState(
                        amount=1000,
                        amount_capturable=1000,
                        amount_received=0,
                        status=IntentStatus.REQUIRES_CAPTURE,
                    ),
                    refund_state=None,
                    stripe_charge_state=StripeChargeState(
                        amount=1000,
                        amount_refunded=999,
                        status=LegacyStripeChargeStatus.SUCCEEDED,
                        error_reason="",
                    ),
                )
            ],
        )

        await self._update_and_verify_cart_payment_states(
            init_cart_payment=cart_payment,
            consumer_charge_id=consumer_charge_id,
            new_cart_payment_state=lower_amount,
            cart_payment_processor=cart_payment_processor,
            cart_payment_repository=cart_payment_repository,
        )

        # 3 attempt to capture, but use mock to fail in between capture and refund
        capture_state = CartPaymentState(
            description="capture cart payment",
            initial_amount=1000,
            amount_delta_update=None,
            expected_amount=1,
            capture_intents=True,
            delay_capture=True,
            payment_intent_states=[
                PaymentIntentState(
                    amount=1,
                    status=IntentStatus.SUCCEEDED,
                    pgp_payment_intent_state=PgpPaymentIntentState(
                        amount=1000,
                        amount_capturable=0,
                        amount_received=1000,
                        status=IntentStatus.SUCCEEDED,
                    ),
                    refund_state=RefundState(
                        status=RefundStatus.SUCCEEDED,
                        amount=999,
                        reason=RefundReason.REQUESTED_BY_CUSTOMER,
                        is_refund_at_capture=True,
                    ),
                    stripe_charge_state=StripeChargeState(
                        amount=1000,
                        amount_refunded=999,
                        status=LegacyStripeChargeStatus.SUCCEEDED,
                        error_reason="",
                    ),
                )
            ],
        )

        bad_exec = InvalidRequestError("i am bad", "param")
        with mock.patch.object(
            cart_payment_processor.cart_payment_interface.stripe_async_client,
            "refund_charge",
            side_effect=bad_exec,
        ):
            with pytest.raises(Exception) as e:
                await self._update_and_verify_cart_payment_states(
                    init_cart_payment=cart_payment,
                    consumer_charge_id=consumer_charge_id,
                    new_cart_payment_state=capture_state,
                    cart_payment_processor=cart_payment_processor,
                    cart_payment_repository=cart_payment_repository,
                )
            assert e.value.orig_error == bad_exec
            updated_payment_intent = await cart_payment_repository.get_payment_intent_by_id_from_primary(
                initial_payment_intent.id
            )
            assert updated_payment_intent
            assert updated_payment_intent.status == IntentStatus.CAPTURING

        # 4 flip back payment intent status
        now = datetime.now(timezone.utc)
        flipped_payment_intent = await cart_payment_repository.update_payment_intent(
            update_payment_intent_status_where_input=UpdatePaymentIntentWhereInput(
                id=updated_payment_intent.id, previous_status=IntentStatus.CAPTURING
            ),
            update_payment_intent_status_set_input=UpdatePaymentIntentSetInput(
                status=IntentStatus.REQUIRES_CAPTURE, updated_at=now
            ),
        )
        assert flipped_payment_intent.status == IntentStatus.REQUIRES_CAPTURE
        with mock.patch.object(
            cart_payment_processor.cart_payment_interface.stripe_async_client,
            "refund_charge",
            wraps=cart_payment_processor.cart_payment_interface.stripe_async_client.refund_charge,
        ) as monitored_refund_charge:
            await self._update_and_verify_cart_payment_states(
                init_cart_payment=cart_payment,
                consumer_charge_id=consumer_charge_id,
                new_cart_payment_state=capture_state,
                cart_payment_processor=cart_payment_processor,
                cart_payment_repository=cart_payment_repository,
            )
        monitored_refund_charge.assert_called_once()
