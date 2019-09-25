import pytest
from unittest.mock import MagicMock

from app.commons.types import CountryCode, Currency
from app.payin.core.exceptions import (
    CartPaymentReadError,
    PayinErrorCode,
    PaymentMethodReadError,
)
from app.payin.core.payer.processor import PayerClient
from app.payin.core.payment_method.processor import PaymentMethodClient
import app.payin.core.cart_payment.processor as processor
from app.payin.core.cart_payment.model import IntentStatus, CartPayment
from app.payin.core.cart_payment.types import LegacyStripeChargeStatus
from app.payin.tests.utils import (
    generate_payment_intent,
    generate_pgp_payment_intent,
    generate_cart_payment,
    generate_legacy_payment,
    generate_legacy_consumer_charge,
    generate_legacy_stripe_charge,
    FunctionMock,
)
import uuid


class TestCartPaymentProcessor:
    """
    Test external facing functions exposed by app/payin/core/cart_payment/processor.py.
    """

    @pytest.fixture
    def request_cart_payment(self):
        return generate_cart_payment()

    @pytest.fixture
    def payment_method_client(self):
        return PaymentMethodClient(
            payment_method_repo=MagicMock(), log=MagicMock(), app_ctxt=MagicMock()
        )

    @pytest.fixture
    def payer_client(self):
        return PayerClient(
            payer_repo=MagicMock(), log=MagicMock(), app_ctxt=MagicMock()
        )

    @pytest.mark.asyncio
    async def test_create_payment_with_no_payment_method(
        self,
        request_cart_payment,
        payer_client,
        payment_method_client,
        cart_payment_repo,
    ):
        mocked_method_fetch = FunctionMock()
        mocked_method_fetch.side_effect = PaymentMethodReadError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND, retryable=False
        )
        payment_method_client.get_raw_payment_method = mocked_method_fetch

        cart_payment_interface = processor.CartPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payer_client=payer_client,
            payment_method_client=payment_method_client,
            payment_repo=cart_payment_repo,
        )
        legacy_payment_interface = processor.LegacyPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payment_repo=cart_payment_repo,
        )
        cart_payment_processor = processor.CartPaymentProcessor(
            cart_payment_interface=cart_payment_interface,
            legacy_payment_interface=legacy_payment_interface,
        )

        with pytest.raises(PaymentMethodReadError) as payment_error:
            await cart_payment_processor.create_payment(
                request_cart_payment=request_cart_payment,
                idempotency_key=str(uuid.uuid4()),
                country=CountryCode.US,
                currency=Currency.USD,
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND.value
        )

    @pytest.mark.asyncio
    async def test_create_payment_with_other_owner(
        self,
        cart_payment_repo,
        request_cart_payment,
        payer_client,
        payment_method_client,
    ):
        mocked_method_fetch = FunctionMock()
        mocked_method_fetch.side_effect = PaymentMethodReadError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH,
            retryable=False,
        )
        payment_method_client.get_raw_payment_method = mocked_method_fetch

        request_cart_payment.payer_id = f"changed-{request_cart_payment.payer_id}"
        cart_payment_interface = processor.CartPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payment_repo=cart_payment_repo,
            payer_client=payer_client,
            payment_method_client=payment_method_client,
        )
        legacy_payment_interface = processor.LegacyPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payment_repo=cart_payment_repo,
        )
        cart_payment_processor = processor.CartPaymentProcessor(
            cart_payment_interface=cart_payment_interface,
            legacy_payment_interface=legacy_payment_interface,
        )

        with pytest.raises(PaymentMethodReadError) as payment_error:
            await cart_payment_processor.create_payment(
                request_cart_payment=request_cart_payment,
                idempotency_key=str(uuid.uuid4()),
                country=CountryCode.US,
                currency=Currency.USD,
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH.value
        )

    @pytest.mark.skip("Not yet implemented")
    @pytest.mark.asyncio
    async def test_invalid_country(self):
        # TODO Invalid currency/country
        pass

    @pytest.mark.skip("Not yet implemented")
    @pytest.mark.asyncio
    async def test_legacy_payment(self):
        # TODO legacy payment, including other payer_id_type
        pass

    @pytest.mark.asyncio
    async def test_create_payment(self, cart_payment_processor, request_cart_payment):
        result_cart_payment, result_legacy_payment = await cart_payment_processor.create_payment(
            request_cart_payment=request_cart_payment,
            idempotency_key=str(uuid.uuid4()),
            country=CountryCode.US,
            currency=Currency.USD,
        )
        assert result_cart_payment
        assert result_cart_payment.id
        assert result_cart_payment.amount == request_cart_payment.amount
        assert (
            result_cart_payment.client_description
            == request_cart_payment.client_description
        )

    @pytest.mark.asyncio
    async def test_create_commando_payment(
        self, cart_payment_processor, request_cart_payment
    ):
        cart_payment_processor.cart_payment_interface.stripe_async_client.commando = (
            True
        )
        result_cart_payment, result_legacy_payment = await cart_payment_processor.create_payment(
            request_cart_payment=request_cart_payment,
            idempotency_key=str(uuid.uuid4()),
            country=CountryCode.US,
            currency=Currency.USD,
        )
        assert result_cart_payment
        assert result_cart_payment.id
        assert result_cart_payment.amount == request_cart_payment.amount
        assert (
            result_cart_payment.client_description
            == request_cart_payment.client_description
        )

    @pytest.mark.asyncio
    async def test_resubmit(self, cart_payment_processor, request_cart_payment):

        intent = generate_payment_intent()
        cart_payment_processor.cart_payment_interface.payment_repo.get_payment_intent_for_idempotency_key = FunctionMock(
            return_value=intent
        )
        cart_payment_processor.cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[generate_pgp_payment_intent(payment_intent_id=intent.id)]
        )

        legacy_payment = generate_legacy_payment()
        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=(request_cart_payment, legacy_payment)
        )

        # Submit when lookup functions mocked above return a result, meaning we have existing cart payment/intent
        result_cart_payment, result_legacy_payment = await cart_payment_processor.create_payment(
            request_cart_payment=request_cart_payment,
            idempotency_key=str(uuid.uuid4()),
            country=CountryCode.US,
            currency=Currency.USD,
        )
        assert result_cart_payment

        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=(result_cart_payment, legacy_payment)
        )

        # Second submission attempt
        second_result_cart_payment, second_result_legacy_payment = await cart_payment_processor.create_payment(
            request_cart_payment=request_cart_payment,
            idempotency_key=str(uuid.uuid4()),
            country=CountryCode.US,
            currency=Currency.USD,
        )
        assert second_result_cart_payment
        assert result_cart_payment == second_result_cart_payment

    @pytest.mark.asyncio
    async def test_update_fake_cart_payment(self, cart_payment_processor):
        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=(None, None)
        )

        with pytest.raises(CartPaymentReadError) as payment_error:
            await cart_payment_processor.update_payment(
                idempotency_key=str(uuid.uuid4()),
                cart_payment_id=uuid.uuid4(),
                payer_id="payer_id",
                amount=500,
                client_description=None,
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.CART_PAYMENT_NOT_FOUND.value
        )

    @pytest.mark.asyncio
    async def test_update_payment_higher(self, cart_payment_processor):
        cart_payment = generate_cart_payment()
        updated_amount = cart_payment.amount + 100
        result = await cart_payment_processor.update_payment(
            idempotency_key=str(uuid.uuid4()),
            cart_payment_id=cart_payment.id,
            payer_id=cart_payment.payer_id,
            amount=updated_amount,
            client_description=None,
        )
        assert result
        assert result.id == cart_payment.id
        assert result.amount == updated_amount

    @pytest.mark.skip("Test not implemented yet")
    @pytest.mark.asyncio
    async def test_update_payment_higher_after_capture(self, cart_payment_processor):
        pass

    @pytest.mark.skip("Test not implemented yet")
    @pytest.mark.asyncio
    async def test_resubmit_updated_amount_higher(self, cart_payment_processor):
        pass

    @pytest.mark.asyncio
    async def test_update_payment_amount_lower(self, cart_payment_processor):
        cart_payment = generate_cart_payment()

        cart_payment_processor.cart_payment_interface.get_cart_payment_intents = FunctionMock(
            return_value=[
                generate_payment_intent(
                    cart_payment_id=cart_payment.id,
                    status=IntentStatus.REQUIRES_CAPTURE,
                )
            ]
        )

        updated_amount = cart_payment.amount - 100
        result = await cart_payment_processor.update_payment(
            idempotency_key=str(uuid.uuid4()),
            cart_payment_id=cart_payment.id,
            payer_id=cart_payment.payer_id,
            amount=updated_amount,
            client_description=None,
        )
        assert result
        assert result.id == cart_payment.id
        assert result.amount == updated_amount

    @pytest.mark.skip("Test not implemented yet")
    @pytest.mark.asyncio
    async def test_resubmit_update_payment_amount_lower(self, cart_payment_processor):
        pass

    @pytest.mark.asyncio
    async def test_cancel_payment_intent_for_uncaptured(self, cart_payment_processor):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status=IntentStatus.REQUIRES_CAPTURE
        )
        result_intent, result_pgp_intent = await cart_payment_processor._cancel_payment_intent(
            cart_payment, payment_intent
        )
        assert result_intent.status == IntentStatus.CANCELLED
        assert result_pgp_intent.status == IntentStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_payment_intent_for_captured(self, cart_payment_processor):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status=IntentStatus.SUCCEEDED
        )
        result_intent, result_pgp_intent = await cart_payment_processor._cancel_payment_intent(
            cart_payment, payment_intent
        )
        # TODO verify expected values
        assert result_intent.amount == 0
        assert result_pgp_intent.amount == 0

    @pytest.mark.asyncio
    async def test_update_state_after_refund_with_provider(
        self, cart_payment_processor
    ):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status=IntentStatus.SUCCEEDED
        )
        pgp_payment_intent = generate_pgp_payment_intent(
            payment_intent_id=payment_intent.id, status=IntentStatus.SUCCEEDED
        )

        provider_refund = (
            await cart_payment_processor.cart_payment_interface.app_context.stripe.refund_charge()
        )

        result_payment_intent, result_pgp_payment_intent = await cart_payment_processor._update_state_after_refund_with_provider(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_refund=provider_refund,
            refund_amount=payment_intent.amount,
        )

        # TODO verify expected values
        assert result_payment_intent.amount == 0
        assert result_pgp_payment_intent.amount == 0

    @pytest.mark.asyncio
    async def test_update_state_after_cancel_with_provider(
        self, cart_payment_processor
    ):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status=IntentStatus.REQUIRES_CAPTURE
        )
        pgp_payment_intent = generate_pgp_payment_intent(
            payment_intent_id=payment_intent.id, status=IntentStatus.REQUIRES_CAPTURE
        )

        result_payment_intent, result_pgp_payment_intent = await cart_payment_processor._update_state_after_cancel_with_provider(
            payment_intent=payment_intent, pgp_payment_intent=pgp_payment_intent
        )

        assert result_payment_intent.status == IntentStatus.CANCELLED
        assert result_pgp_payment_intent.status == IntentStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_update_state_after_submit_to_provider(self, cart_payment_processor):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status=IntentStatus.REQUIRES_CAPTURE
        )
        pgp_payment_intent = generate_pgp_payment_intent(
            payment_intent_id=payment_intent.id, status=IntentStatus.REQUIRES_CAPTURE
        )

        provider_payment_intent = (
            await cart_payment_processor.cart_payment_interface.app_context.stripe.create_payment_intent()
        )

        result_payment_intent, result_pgp_payment_intent, result_stripe_charge = await cart_payment_processor._update_state_after_submit_to_provider(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_payment_intent=provider_payment_intent,
            cart_payment=cart_payment,
            correlation_ids=cart_payment.correlation_ids,
            legacy_payment=generate_legacy_payment(),
            legacy_stripe_charge=generate_legacy_stripe_charge(),
        )

        assert result_payment_intent.status == IntentStatus.REQUIRES_CAPTURE
        assert result_pgp_payment_intent.status == IntentStatus.REQUIRES_CAPTURE
        assert result_stripe_charge.status == LegacyStripeChargeStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_cancel_payment(self, cart_payment_processor, request_cart_payment):
        result = await cart_payment_processor.cancel_payment(request_cart_payment.id)
        assert result
        assert type(result) == CartPayment

    @pytest.mark.asyncio
    async def test_cancel_payment_fake_cart_payment(self, cart_payment_processor):
        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=(None, None)
        )

        with pytest.raises(CartPaymentReadError) as payment_error:
            await cart_payment_processor.cancel_payment(cart_payment_id=uuid.uuid4())
        assert (
            payment_error.value.error_code
            == PayinErrorCode.CART_PAYMENT_NOT_FOUND.value
        )

    @pytest.mark.asyncio
    async def test_update_payment_for_legacy_charge(self, cart_payment_processor):
        legacy_charge = generate_legacy_consumer_charge()
        legacy_payment = generate_legacy_payment(dd_charge_id=legacy_charge.id)
        client_description = f"updated description for {legacy_charge.id}"
        result = await cart_payment_processor.update_payment_for_legacy_charge(
            idempotency_key=str(uuid.uuid4()),
            dd_charge_id=legacy_charge.id,
            payer_id=None,
            amount=1500,
            client_description=client_description,
            request_legacy_payment=legacy_payment,
        )
        assert result
        assert result.amount == 1500
        assert result.client_description == client_description

    @pytest.mark.asyncio
    async def test_update_payment_for_legacy_charge_fake_cart_payment(
        self, cart_payment_processor
    ):
        legacy_charge = generate_legacy_consumer_charge()
        cart_payment_processor.legacy_payment_interface.payment_repo.get_payment_intent_for_legacy_consumer_charge_id = FunctionMock(
            return_value=None
        )
        with pytest.raises(CartPaymentReadError) as payment_error:
            await cart_payment_processor.update_payment_for_legacy_charge(
                idempotency_key=str(uuid.uuid4()),
                dd_charge_id=legacy_charge.id,
                payer_id=None,
                amount=1500,
                client_description="description",
                request_legacy_payment=None,
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.CART_PAYMENT_NOT_FOUND.value
        )

    @pytest.mark.asyncio
    async def test_cancel_payment_for_legacy_charge(self, cart_payment_processor):
        legacy_charge = generate_legacy_consumer_charge()
        result = await cart_payment_processor.cancel_payment_for_legacy_charge(
            dd_charge_id=legacy_charge.id
        )
        assert result
        assert type(result) == CartPayment

    @pytest.mark.asyncio
    async def test_cancel_payment_for_legacy_charge_fake_cart_payment(
        self, cart_payment_processor
    ):
        legacy_charge = generate_legacy_consumer_charge()
        cart_payment_processor.legacy_payment_interface.payment_repo.get_payment_intent_for_legacy_consumer_charge_id = FunctionMock(
            return_value=None
        )

        with pytest.raises(CartPaymentReadError) as payment_error:
            await cart_payment_processor.cancel_payment_for_legacy_charge(
                dd_charge_id=legacy_charge.id
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.CART_PAYMENT_NOT_FOUND.value
        )
