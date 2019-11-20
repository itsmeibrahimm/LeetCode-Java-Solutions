import pytest
from asyncio import gather
from uuid import uuid4

from app.conftest import RuntimeContextManager, RuntimeSetter
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.exceptions import CartPaymentReadError, PayinErrorCode
from app.payin.core.payer.model import Payer
from app.payin.core.payment_method.model import PaymentMethod
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.test_integration.processors.cart_payment_test_base import CartPaymentTest


class TestConcurrentCartPayments(CartPaymentTest):
    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    async def test_concurrent_access_with_cart_payment_locking(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
        runtime_setter: RuntimeSetter,
    ):
        cart_payment = await self._prepare_cart_payment(
            payer=payer,
            payment_method=payment_method,
            delay_capture=True,
            cart_payment_processor=cart_payment_processor,
            idempotency_key=str(uuid4()),
        )
        assert cart_payment

        payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )

        assert len(payment_intents) == 1, "only expect 1 initial payment_intent"
        init_payment_intent = payment_intents[0]
        consumer_charge_id = init_payment_intent.legacy_consumer_charge_id

        first_update_attempt = self._update_cart_payment(
            cart_payment_processor=cart_payment_processor,
            existing_cart_payment=cart_payment,
            idempotency_key=str(uuid4()),
            payer_id=payer.id,
            delta_amount=50000,
            consumer_charge_id=consumer_charge_id,
        )
        second_update_attempt = self._update_cart_payment(
            cart_payment_processor=cart_payment_processor,
            existing_cart_payment=cart_payment,
            idempotency_key=str(uuid4()),
            payer_id=payer.id,
            delta_amount=60000,
            consumer_charge_id=consumer_charge_id,
        )

        with RuntimeContextManager(
            "payin/feature-flags/enable_payin_cart_payment_update_locking.bool",
            True,
            runtime_setter,
        ):
            results = await gather(
                first_update_attempt, second_update_attempt, return_exceptions=True
            )
            access_exceptions = list(
                filter(lambda x: type(x) == CartPaymentReadError, results)
            )

            # When two attempts to update the same cart payment happen near the same time, one should succeed and the other
            # will fail since we cannot obtain the lock for updating the payment.
            assert len(access_exceptions) == 1
            assert (
                access_exceptions[0].error_code
                == PayinErrorCode.CART_PAYMENT_CONCURRENT_ACCESS_ERROR
            )
            assert access_exceptions[0].retryable == True
