import uuid
from copy import deepcopy
from unittest.mock import MagicMock

import asynctest
import pytest
from asynctest import create_autospec

from app.commons.providers.stripe.stripe_models import CreatePaymentIntent
from app.payin.conftest import PgpPaymentIntentFactory, PaymentIntentFactory
from app.payin.core.cart_payment.model import (
    PaymentIntent,
    PgpPaymentIntent,
    PaymentCharge,
    PgpPaymentCharge,
)
from app.payin.core.cart_payment.processor import CartPaymentInterface
from app.payin.core.cart_payment.types import IntentStatus, ChargeStatus
from app.payin.core.exceptions import (
    PaymentIntentRefundError,
    CartPaymentCreateError,
    PaymentChargeRefundError,
    PaymentIntentCancelError,
    PaymentIntentCaptureError,
    PayinErrorCode,
    PaymentIntentCouldNotBeUpdatedError,
    PaymentIntentConcurrentAccessError,
)
from app.payin.tests.utils import (
    generate_payment_intent,
    generate_pgp_payment_intent,
    generate_cart_payment,
    generate_provider_charges,
    FunctionMock,
)


class TestCartPaymentInterface:
    """
    Test CartPaymentInterface class functions.
    """

    @pytest.mark.asyncio
    async def test_find_existing_no_matches(self, cart_payment_interface):
        mock_intent_search = FunctionMock(return_value=None)
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
        cart_payment_interface.payment_repo.get_payment_intent_for_idempotency_key = FunctionMock(
            return_value=intent
        )

        # Mock function to find cart payment
        cart_payment = MagicMock()
        cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=cart_payment
        )

        result = await cart_payment_interface._find_existing(
            payer_id="payer_id", idempotency_key="idempotency_key"
        )
        assert result == (cart_payment, intent)

    @pytest.mark.asyncio
    async def test_get_cart_payment(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=cart_payment
        )

        result = await cart_payment_interface._get_cart_payment(cart_payment.id)
        assert result == cart_payment

    @pytest.mark.asyncio
    async def test_get_cart_payment_no_match(self, cart_payment_interface):
        cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=None
        )

        result = await cart_payment_interface._get_cart_payment(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_most_recent_pgp_payment_intent(self, cart_payment_interface):
        first_pgp_intent = generate_pgp_payment_intent()
        second_pgp_intent = generate_pgp_payment_intent()

        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[first_pgp_intent, second_pgp_intent]
        )

        result = await cart_payment_interface._get_most_recent_pgp_payment_intent(
            MagicMock()
        )
        assert result == second_pgp_intent

    @pytest.mark.asyncio
    async def test_get_most_recent_intent(self, cart_payment_interface):
        first_intent = generate_payment_intent()
        second_intent = generate_payment_intent()

        result = cart_payment_interface._get_most_recent_intent(
            [first_intent, second_intent]
        )
        assert result == second_intent

    def test_transform_method_for_stripe(self, cart_payment_interface):
        assert (
            cart_payment_interface._transform_method_for_stripe("auto") == "automatic"
        )
        assert cart_payment_interface._transform_method_for_stripe("manual") == "manual"

    def test_get_provider_capture_method(self, cart_payment_interface):
        intent = generate_payment_intent(capture_method="manual")
        result = cart_payment_interface._get_provider_capture_method(intent)
        assert result == CreatePaymentIntent.CaptureMethod.MANUAL

        intent = generate_payment_intent(capture_method="auto")
        result = cart_payment_interface._get_provider_capture_method(intent)
        assert result == CreatePaymentIntent.CaptureMethod.AUTOMATIC

    def test_get_provider_confirmation_method(self, cart_payment_interface):
        intent = generate_payment_intent(confirmation_method="manual")
        result = cart_payment_interface._get_provider_confirmation_method(intent)
        assert result == CreatePaymentIntent.ConfirmationMethod.MANUAL

        intent = generate_payment_intent(confirmation_method="auto")
        result = cart_payment_interface._get_provider_confirmation_method(intent)
        assert result == CreatePaymentIntent.ConfirmationMethod.AUTOMATIC

    def test_get_provider_future_usage(self, cart_payment_interface):
        intent = generate_payment_intent(capture_method="manual")
        result = cart_payment_interface._get_provider_future_usage(intent)
        assert result == CreatePaymentIntent.SetupFutureUsage.OFF_SESSION

        intent = generate_payment_intent(capture_method="auto")
        result = cart_payment_interface._get_provider_future_usage(intent)
        assert result == CreatePaymentIntent.SetupFutureUsage.ON_SESSION

    def test_intent_submit_status_evaluation(self, cart_payment_interface):
        intent = generate_payment_intent(status="init")
        assert cart_payment_interface._is_payment_intent_submitted(intent) is False

        intent = generate_payment_intent(status="processing")
        assert cart_payment_interface._is_payment_intent_submitted(intent) is True

    def test_intent_can_be_cancelled(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.FAILED)
        assert cart_payment_interface._can_payment_intent_be_cancelled(intent) is False

        intent = generate_payment_intent(status=IntentStatus.SUCCEEDED)
        assert cart_payment_interface._can_payment_intent_be_cancelled(intent) is False

        intent = generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)
        assert cart_payment_interface._can_payment_intent_be_cancelled(intent) is True

    def test_can_payment_intent_be_refunded(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.FAILED)
        assert cart_payment_interface._can_payment_intent_be_refunded(intent) is False

        intent = generate_payment_intent(status=IntentStatus.SUCCEEDED)
        assert cart_payment_interface._can_payment_intent_be_refunded(intent) is True

        intent = generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)
        assert cart_payment_interface._can_payment_intent_be_refunded(intent) is False

    def test_can_pgp_payment_intent_be_refunded(self, cart_payment_interface):
        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.FAILED)
        assert (
            cart_payment_interface._can_pgp_payment_intent_be_refunded(pgp_intent)
            is False
        )

        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.SUCCEEDED)
        assert (
            cart_payment_interface._can_pgp_payment_intent_be_refunded(pgp_intent)
            is True
        )

        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)
        assert (
            cart_payment_interface._can_pgp_payment_intent_be_refunded(pgp_intent)
            is False
        )

    def test_does_intent_require_capture(self, cart_payment_interface):
        intent = generate_payment_intent(status="init")
        assert cart_payment_interface._does_intent_require_capture(intent) is False

        intent = generate_payment_intent(status="requires_capture")
        assert cart_payment_interface._does_intent_require_capture(intent) is True

    def test_get_intent_status_from_provider_status(self, cart_payment_interface):
        intent_status = cart_payment_interface._get_intent_status_from_provider_status(
            "requires_capture"
        )
        assert intent_status == IntentStatus.REQUIRES_CAPTURE

        with pytest.raises(ValueError):
            cart_payment_interface._get_intent_status_from_provider_status(
                "coffee_beans"
            )

    def test_pgp_intent_status_evaluation(self, cart_payment_interface):
        intent = generate_pgp_payment_intent(status="init")
        assert cart_payment_interface._is_pgp_payment_intent_submitted(intent) is False

        intent = generate_pgp_payment_intent(status="processing")
        assert cart_payment_interface._is_pgp_payment_intent_submitted(intent) is True

    def test_get_cart_payment_submission_pgp_intent(self, cart_payment_interface):
        first_intent = generate_pgp_payment_intent(status="init")
        second_intent = generate_pgp_payment_intent(status="init")
        pgp_intents = [first_intent, second_intent]
        selected_intent = cart_payment_interface._get_cart_payment_submission_pgp_intent(
            pgp_intents
        )
        assert selected_intent == first_intent

    def test_filter_for_payment_intent_by_status(self, cart_payment_interface):
        succeeded_intent = generate_payment_intent(status="succeeded")
        intents = [
            generate_payment_intent(status="init"),
            succeeded_intent,
            generate_payment_intent(status="init"),
        ]
        result = cart_payment_interface._filter_payment_intents_by_state(
            intents, IntentStatus.SUCCEEDED
        )
        assert result == [succeeded_intent]

        result = cart_payment_interface._filter_payment_intents_by_state(
            intents, IntentStatus.INIT
        )
        assert result == [intents[0], intents[2]]

        result = cart_payment_interface._filter_payment_intents_by_state(
            intents, IntentStatus.FAILED
        )
        assert result == []

    def test_filter_for_payment_intent_by_idempotency_key(self, cart_payment_interface):
        target_intent = generate_payment_intent()
        intents = [generate_payment_intent(), target_intent, generate_payment_intent()]
        result = cart_payment_interface._filter_payment_intents_by_idempotency_key(
            intents, target_intent.idempotency_key
        )
        assert result == target_intent

        result = cart_payment_interface._filter_payment_intents_by_idempotency_key(
            intents, f"{target_intent.idempotency_key}-fake"
        )
        assert result is None

    def test_filter_payment_intents_by_function(self, cart_payment_interface):
        target_payment_intent = generate_payment_intent()
        second_intent = generate_payment_intent()

        def filter_function(payment_intent: PaymentIntent) -> bool:
            return payment_intent.id == target_payment_intent.id

        result = cart_payment_interface._filter_payment_intents_by_function(
            [target_payment_intent, second_intent], filter_function
        )
        assert result == [target_payment_intent]

    def test_get_charge_status_from_intent_status(self, cart_payment_interface):
        charge_status = cart_payment_interface._get_charge_status_from_intent_status(
            IntentStatus.SUCCEEDED
        )
        assert charge_status == ChargeStatus.SUCCEEDED

        charge_status = cart_payment_interface._get_charge_status_from_intent_status(
            IntentStatus.FAILED
        )
        assert charge_status == ChargeStatus.FAILED

        charge_status = cart_payment_interface._get_charge_status_from_intent_status(
            IntentStatus.REQUIRES_CAPTURE
        )
        assert charge_status == ChargeStatus.REQUIRES_CAPTURE

        charge_status = cart_payment_interface._get_charge_status_from_intent_status(
            IntentStatus.CANCELLED
        )
        assert charge_status == ChargeStatus.CANCELLED

        with pytest.raises(ValueError):
            cart_payment_interface._get_charge_status_from_intent_status(
                IntentStatus.INIT
            )

    def test_is_amount_adjusted_higher(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.amount = 500

        assert (
            cart_payment_interface._is_amount_adjusted_higher(cart_payment, 400)
            is False
        )
        assert (
            cart_payment_interface._is_amount_adjusted_higher(cart_payment, 500)
            is False
        )
        assert (
            cart_payment_interface._is_amount_adjusted_higher(cart_payment, 600) is True
        )

    def test_is_amount_adjusted_lower(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.amount = 500

        assert (
            cart_payment_interface._is_amount_adjusted_lower(cart_payment, 400) is True
        )
        assert (
            cart_payment_interface._is_amount_adjusted_lower(cart_payment, 500) is False
        )
        assert (
            cart_payment_interface._is_amount_adjusted_lower(cart_payment, 600) is False
        )

    @pytest.mark.asyncio
    async def test_submit_payment_to_provider(self, cart_payment_interface):
        intent = generate_payment_intent()
        pgp_intent = generate_pgp_payment_intent(payment_intent_id=intent.id)
        result_intent, result_pgp_intent = await cart_payment_interface._submit_payment_to_provider(
            payment_intent=intent,
            pgp_payment_intent=pgp_intent,
            provider_payment_resource_id="payment_resource_id",
            provider_customer_resource_id="customer_resource_id",
        )

        assert result_intent
        assert result_intent.status == IntentStatus.REQUIRES_CAPTURE
        assert result_intent.amount == intent.amount

        assert result_pgp_intent
        assert result_pgp_intent.status == IntentStatus.REQUIRES_CAPTURE
        assert result_pgp_intent.amount == pgp_intent.amount

    @pytest.mark.asyncio
    async def test_create_provider_payment(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        response = await cart_payment_interface._create_provider_payment(
            intent, pgp_intent, "payment_resource_id", "customer_resource_id"
        )
        assert response

    @pytest.mark.asyncio
    async def test_create_provider_payment_error(self, cart_payment_interface):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = Exception()
        cart_payment_interface.app_context.stripe.create_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        with pytest.raises(CartPaymentCreateError) as payment_error:
            await cart_payment_interface._create_provider_payment(
                intent, pgp_intent, "payment_resource_id", "customer_resource_id"
            )

        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR
        )

    @pytest.mark.asyncio
    async def test_cancel_provider_payment_charge(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        response = await cart_payment_interface._cancel_provider_payment_charge(
            intent, pgp_intent, "abandoned"
        )
        assert response

    @pytest.mark.asyncio
    async def test_cancel_provider_payment_charge_error(self, cart_payment_interface):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = Exception()
        cart_payment_interface.app_context.stripe.cancel_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        with pytest.raises(PaymentChargeRefundError) as payment_error:
            await cart_payment_interface._cancel_provider_payment_charge(
                intent, pgp_intent, "abandoned"
            )

        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
        )

    @pytest.mark.asyncio
    async def test_refund_provider_payment(self, cart_payment_interface):
        intent = generate_payment_intent(status="succeeded")
        pgp_intent = generate_pgp_payment_intent(status="succeeded")
        response = await cart_payment_interface._refund_provider_payment(
            payment_intent=intent,
            pgp_payment_intent=pgp_intent,
            reason="abandoned",
            refund_amount=500,
        )
        assert response

    @pytest.mark.asyncio
    async def test_refund_provider_payment_error(self, cart_payment_interface):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = Exception()
        cart_payment_interface.app_context.stripe.refund_charge = mocked_stripe_function

        intent = generate_payment_intent(status="succeeded")
        pgp_intent = generate_pgp_payment_intent(status="succeeded")

        with pytest.raises(PaymentIntentCancelError) as payment_error:
            await cart_payment_interface._refund_provider_payment(
                payment_intent=intent,
                pgp_payment_intent=pgp_intent,
                reason="abandoned",
                refund_amount=500,
            )

        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
        )

    @pytest.mark.asyncio
    async def test_capture_payment_with_provider(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        response = await cart_payment_interface._capture_payment_with_provider(
            intent, pgp_intent
        )
        assert response

    @pytest.mark.asyncio
    async def test_capture_payment_with_provider_error(self, cart_payment_interface):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = Exception()
        cart_payment_interface.app_context.stripe.capture_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        with pytest.raises(PaymentIntentCaptureError) as payment_error:
            await cart_payment_interface._capture_payment_with_provider(
                intent, pgp_intent
            )

        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_CAPTURE_STRIPE_ERROR
        )

    def test_is_accessible(self, cart_payment_interface):
        # Stub function: return value is fixed
        assert (
            cart_payment_interface.is_accessible(
                cart_payment=MagicMock(),
                request_payer_id="payer_id",
                credential_owner="credential_ower",
            )
            is True
        )

    def test_is_capture_immediate(self, cart_payment_interface):
        # Stub function: return value is fixed
        intent = generate_payment_intent()
        assert cart_payment_interface._is_capture_immediate(intent) is False

    def test_populate_cart_payment_for_response(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.capture_method = "manual"
        cart_payment.payer_statement_description = "Fill in here"
        intent = generate_payment_intent(
            status="requires_capture", capture_method="auto"
        )
        pgp_intent = generate_pgp_payment_intent(
            status="requires_capture", capture_method="auto"
        )

        original_cart_payment = deepcopy(cart_payment)
        cart_payment_interface._populate_cart_payment_for_response(
            cart_payment, intent, pgp_intent
        )

        # Fields populated based on related objects
        assert cart_payment.payment_method_id == pgp_intent.payment_method_resource_id
        assert cart_payment.payer_statement_description == intent.statement_descriptor
        assert cart_payment.capture_method == intent.capture_method

        # Unchanged attributes
        assert cart_payment.id == original_cart_payment.id
        assert cart_payment.amount == original_cart_payment.amount
        assert cart_payment.payer_id == original_cart_payment.payer_id
        assert cart_payment.cart_metadata == original_cart_payment.cart_metadata
        assert cart_payment.created_at == original_cart_payment.created_at
        assert cart_payment.updated_at == original_cart_payment.updated_at
        assert cart_payment.deleted_at == original_cart_payment.deleted_at
        assert (
            cart_payment.client_description == original_cart_payment.client_description
        )
        assert cart_payment.legacy_payment == original_cart_payment.legacy_payment
        assert cart_payment.split_payment == original_cart_payment.split_payment

    @pytest.mark.asyncio
    async def test_create_new_intent_pair(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        result_intent, result_pgp_intent = await cart_payment_interface._create_new_intent_pair(
            cart_payment=cart_payment,
            idempotency_key="idempotency_key",
            payment_method_id=cart_payment.payment_method_id,
            amount=cart_payment.amount,
            country="US",
            currency="USD",
            capture_method=cart_payment.capture_method,
            payer_statement_description=None,
        )

        expected_payment_intent = PaymentIntent(
            id=result_intent.id,  # Generated field
            cart_payment_id=cart_payment.id,
            idempotency_key="idempotency_key",
            amount_initiated=cart_payment.amount,
            amount=cart_payment.amount,
            amount_capturable=None,
            amount_received=None,
            application_fee_amount=None,
            capture_method="manual",
            confirmation_method="manual",
            country="US",
            currency="USD",
            status=IntentStatus.INIT,
            statement_descriptor=None,
            created_at=result_intent.created_at,  # Generated field
            updated_at=result_intent.updated_at,  # Generated field
            captured_at=None,
            cancelled_at=None,
        )

        assert result_intent == expected_payment_intent
        # For generated fields we expect to be populated, exact value not know ahead of time, but
        # ensure we have a value.
        assert result_intent.id
        assert result_intent.created_at
        assert result_intent.updated_at

        expected_pgp_intent = PgpPaymentIntent(
            id=result_pgp_intent.id,  # Generated field
            payment_intent_id=result_intent.id,
            idempotency_key="idempotency_key",
            provider="stripe",
            status=IntentStatus.INIT,
            resource_id=None,
            charge_resource_id=None,
            invoice_resource_id=None,
            payment_method_resource_id=cart_payment.payment_method_id,
            currency="USD",
            amount=cart_payment.amount,
            amount_capturable=None,
            amount_received=None,
            application_fee_amount=None,
            capture_method="manual",
            confirmation_method="manual",
            payout_account_id=None,
            created_at=result_pgp_intent.created_at,  # Generated field
            updated_at=result_pgp_intent.updated_at,  # Generated field
            captured_at=None,
            cancelled_at=None,
        )

        assert result_pgp_intent == expected_pgp_intent
        # For generated fields we expect to be populated, exact value not know ahead of time, but
        # ensure we have a value.
        assert result_intent.id
        assert result_intent.created_at
        assert result_intent.updated_at

    @pytest.mark.asyncio
    async def test_create_new_charge_pair(self, cart_payment_interface):
        payment_intent = generate_payment_intent()
        pgp_payment_intent = generate_pgp_payment_intent()

        provider_intent = (
            await cart_payment_interface.app_context.stripe.capture_payment_intent()
        )
        provider_intent.charges = generate_provider_charges(
            payment_intent, pgp_payment_intent
        )

        result_payment_charge, result_pgp_charge = await cart_payment_interface._create_new_charge_pair(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_intent=provider_intent,
        )

        expected_payment_charge = PaymentCharge(
            id=result_payment_charge.id,  # Generated
            payment_intent_id=payment_intent.id,
            provider=pgp_payment_intent.provider,
            idempotency_key=result_payment_charge.idempotency_key,
            status=ChargeStatus.REQUIRES_CAPTURE,
            currency=payment_intent.currency,
            amount=payment_intent.amount,
            amount_refunded=0,
            application_fee_amount=payment_intent.application_fee_amount,
            payout_account_id=pgp_payment_intent.payout_account_id,
            created_at=result_payment_charge.created_at,  # Generated
            updated_at=result_payment_charge.updated_at,  # Generated
            captured_at=None,
            cancelled_at=None,
        )

        assert result_payment_charge == expected_payment_charge
        # Verify we have values for generated fields
        assert result_payment_charge.id
        assert result_payment_charge.idempotency_key
        assert result_payment_charge.created_at
        assert result_payment_charge.updated_at

        expected_pgp_charge = PgpPaymentCharge(
            id=result_pgp_charge.id,  # Generated
            payment_charge_id=result_payment_charge.id,
            provider=pgp_payment_intent.provider,
            idempotency_key=result_payment_charge.idempotency_key,
            status=ChargeStatus.REQUIRES_CAPTURE,
            currency=payment_intent.currency,
            amount=payment_intent.amount,
            amount_refunded=0,
            application_fee_amount=payment_intent.application_fee_amount,
            payout_account_id=pgp_payment_intent.payout_account_id,
            resource_id=provider_intent.charges.data[0].id,
            intent_resource_id=provider_intent.charges.data[0].payment_intent,
            invoice_resource_id=provider_intent.charges.data[0].invoice,
            payment_method_resource_id=provider_intent.charges.data[0].payment_method,
            created_at=result_pgp_charge.created_at,  # Generated
            updated_at=result_pgp_charge.updated_at,  # Generated
            captured_at=None,
            cancelled_at=None,
        )

        assert result_pgp_charge == expected_pgp_charge
        # Verify we have values for generated fields
        assert result_pgp_charge.id
        assert result_pgp_charge.created_at
        assert result_pgp_charge.updated_at

    @pytest.mark.asyncio
    async def test_update_charge_pair_after_capture(self, cart_payment_interface):
        payment_intent = generate_payment_intent(status="requires_capture")
        pgp_payment_intent = generate_pgp_payment_intent(
            status="requires_capture", payment_intent_id=payment_intent.id
        )
        provider_intent = (
            await cart_payment_interface.app_context.stripe.capture_payment_intent()
        )
        provider_intent.charges = generate_provider_charges(
            payment_intent, pgp_payment_intent
        )

        result_payment_charge, result_pgp_charge = await cart_payment_interface._update_charge_pair_after_capture(
            payment_intent=payment_intent,
            status=ChargeStatus.SUCCEEDED,
            provider_intent=provider_intent,
        )

        assert result_payment_charge
        assert result_payment_charge.status == ChargeStatus.SUCCEEDED
        assert result_payment_charge.payment_intent_id == payment_intent.id

        assert result_pgp_charge
        assert result_pgp_charge.status == ChargeStatus.SUCCEEDED
        assert result_pgp_charge.amount == provider_intent.charges.data[0].amount
        assert (
            result_pgp_charge.amount_refunded
            == provider_intent.charges.data[0].amount_refunded
        )

    @pytest.mark.asyncio
    async def test_update_charge_pair_after_cancel(self, cart_payment_interface):
        payment_intent = generate_payment_intent()
        result_payment_charge, result_pgp_charge = await cart_payment_interface._update_charge_pair_after_cancel(
            payment_intent=payment_intent, status=ChargeStatus.CANCELLED
        )

        assert result_payment_charge
        assert result_payment_charge.status == ChargeStatus.CANCELLED

        assert result_pgp_charge
        assert result_pgp_charge.status == ChargeStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_update_charge_pair_after_refund(self, cart_payment_interface):
        payment_intent = generate_payment_intent(status="succeeded")
        provider_refund = (
            await cart_payment_interface.app_context.stripe.refund_charge()
        )
        result_payment_charge, result_pgp_charge = await cart_payment_interface._update_charge_pair_after_refund(
            payment_intent=payment_intent, provider_refund=provider_refund
        )

        assert result_payment_charge
        assert result_payment_charge.status == ChargeStatus(provider_refund.status)
        assert result_payment_charge.amount_refunded == provider_refund.amount

        assert result_pgp_charge
        assert result_pgp_charge.status == ChargeStatus(provider_refund.status)
        assert result_pgp_charge.amount == payment_intent.amount
        assert result_pgp_charge.amount_refunded == provider_refund.amount

    @pytest.mark.asyncio
    async def test_update_charge_pair_after_amount_reduction(
        self, cart_payment_interface
    ):
        payment_intent = generate_payment_intent()
        result_payment_charge, result_pgp_charge = await cart_payment_interface._update_charge_pair_after_amount_reduction(
            payment_intent=payment_intent, amount=600
        )

        assert result_payment_charge
        assert result_payment_charge.amount == 600

        assert result_pgp_charge
        assert result_pgp_charge.amount == 600

    @pytest.mark.asyncio
    async def test_update_pgp_charge_from_provider(self, cart_payment_interface):
        provider_intent = (
            await cart_payment_interface.app_context.stripe.capture_payment_intent()
        )
        provider_intent.charges = generate_provider_charges(
            generate_payment_intent(), generate_pgp_payment_intent()
        )

        result_pgp_charge = await cart_payment_interface._update_pgp_charge_from_provider(
            payment_charge_id=uuid.uuid4(),
            status=ChargeStatus.SUCCEEDED,
            provider_intent=provider_intent,
        )

        assert result_pgp_charge
        assert result_pgp_charge.status == ChargeStatus.SUCCEEDED
        assert result_pgp_charge.amount == provider_intent.charges.data[0].amount
        assert (
            result_pgp_charge.amount_refunded
            == provider_intent.charges.data[0].amount_refunded
        )

    @pytest.mark.asyncio
    async def test_update_cart_payment_attributes(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        result = await cart_payment_interface._update_cart_payment_attributes(
            cart_payment=deepcopy(cart_payment),
            idempotency_key=str(uuid.uuid4()),
            payment_intent=generate_payment_intent(),
            pgp_payment_intent=generate_pgp_payment_intent(),
            amount=100,
            client_description=None,
        )

        assert result
        assert result.id
        assert result.amount == 100
        assert result.client_description is None

    @pytest.mark.asyncio
    async def test_submit_new_payment(self, cart_payment_interface, stripe_interface):
        # Parameters for function
        request_cart_payment = generate_cart_payment()
        payment_resource_id = "payment_resource_id"
        customer_resource_id = "customer_resource_id"
        idempotency_key = str(uuid.uuid4())
        country = "US"
        currency = "USD"
        client_description = "test"
        result_cart_payment, result_payment_intent = await cart_payment_interface.submit_new_payment(
            request_cart_payment,
            payment_resource_id,
            customer_resource_id,
            idempotency_key,
            country,
            currency,
            client_description,
        )

        expected_cart_payment = deepcopy(request_cart_payment)
        # Fill in generated fields
        expected_cart_payment.created_at = result_cart_payment.created_at
        expected_cart_payment.updated_at = result_cart_payment.updated_at

        assert result_cart_payment == expected_cart_payment
        # Verify generated fields have actual values
        assert result_cart_payment.created_at
        assert result_cart_payment.updated_at

        expected_payment_intent = PaymentIntent(
            id=result_payment_intent.id,  # Generated field
            cart_payment_id=request_cart_payment.id,
            idempotency_key=idempotency_key,
            amount_initiated=request_cart_payment.amount,
            amount=request_cart_payment.amount,
            amount_capturable=None,
            amount_received=None,
            application_fee_amount=None,
            capture_method="manual",
            confirmation_method="manual",
            country=country,
            currency=currency,
            status=IntentStatus.INIT,
            statement_descriptor=None,
            created_at=result_payment_intent.created_at,  # Generated field
            updated_at=result_payment_intent.updated_at,  # Generated field
            captured_at=None,
            cancelled_at=None,
        )
        assert result_payment_intent
        assert result_payment_intent == expected_payment_intent
        assert result_payment_intent.id
        assert result_payment_intent.created_at
        assert result_payment_intent.updated_at

    @pytest.mark.asyncio
    async def test_resubmit_existing_payment(self, cart_payment_interface):
        # Parameters for function
        request_cart_payment = generate_cart_payment()
        intent = generate_payment_intent(cart_payment_id=request_cart_payment.id)
        # pgp_intent = generate_pgp_payment_intent()
        payment_resource_id = "payment_resource_id"
        customer_resource_id = "customer_resource_id"

        # Already submitted before
        response = await cart_payment_interface.resubmit_existing_payment(
            request_cart_payment,
            generate_payment_intent(status=IntentStatus.SUCCEEDED),
            payment_resource_id,
            customer_resource_id,
        )
        assert response == request_cart_payment

        # Success case
        response = await cart_payment_interface.resubmit_existing_payment(
            request_cart_payment, intent, payment_resource_id, customer_resource_id
        )
        assert response == request_cart_payment

    @pytest.mark.asyncio
    async def test_cancel_intent(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        result_intent, result_pgp_intent = await cart_payment_interface._cancel_intent(
            payment_intent=intent, pgp_payment_intents=[pgp_intent]
        )

        assert result_intent
        assert result_intent.status == IntentStatus.CANCELLED

        assert result_pgp_intent
        assert result_pgp_intent.status == IntentStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_refund_intent_invalid_state(self, cart_payment_interface):
        payment_intent = generate_payment_intent()
        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)

        with pytest.raises(PaymentIntentRefundError):
            await cart_payment_interface._refund_intent(
                payment_intent=payment_intent,
                pgp_payment_intents=[pgp_intent],
                refund_amount=300,
            )

    @pytest.mark.asyncio
    async def test_refund_intent(self, cart_payment_interface):
        initial_amount = 500
        refund_amount = 300
        payment_intent = generate_payment_intent(
            status=IntentStatus.SUCCEEDED, amount=initial_amount
        )
        pgp_intent = generate_pgp_payment_intent(
            status=IntentStatus.SUCCEEDED, amount=initial_amount
        )

        result_intent, result_pgp_intent = await cart_payment_interface._refund_intent(
            payment_intent=payment_intent,
            pgp_payment_intents=[pgp_intent],
            refund_amount=refund_amount,
        )

        assert result_intent
        assert result_intent.amount == (initial_amount - refund_amount)

    @pytest.mark.asyncio
    async def test_resubmit_add_amount_to_cart_payment(self, cart_payment_interface):
        # Already processed
        cart_payment = generate_cart_payment()
        intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="requires_capture"
        )
        result_intent, result_pgp_intent = await cart_payment_interface._resubmit_add_amount_to_cart_payment(
            cart_payment, intent
        )

        assert result_intent
        assert result_intent.status == IntentStatus.REQUIRES_CAPTURE

        # Resubmit, with need to call out to provider
        intent = generate_payment_intent(cart_payment_id=cart_payment.id, status="init")
        result_intent, result_pgp_intent = await cart_payment_interface._resubmit_add_amount_to_cart_payment(
            cart_payment, intent
        )

        assert result_intent
        assert result_intent.status == IntentStatus.REQUIRES_CAPTURE

    @pytest.mark.asyncio
    async def test_submit_amount_increase_to_cart_payment(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="requires_capture"
        )

        result_intent, result_pgp_intent = await cart_payment_interface._submit_amount_increase_to_cart_payment(
            cart_payment=cart_payment,
            most_recent_intent=payment_intent,
            amount=850,
            idempotency_key="id_key_850",
        )

        assert result_intent
        assert result_intent.status == IntentStatus.REQUIRES_CAPTURE

        assert result_pgp_intent
        assert result_pgp_intent.status == IntentStatus.REQUIRES_CAPTURE

    @pytest.mark.asyncio
    async def test_add_amount_to_cart_payment(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        result_cart_payment = await cart_payment_interface._add_amount_to_cart_payment(
            cart_payment=cart_payment,
            idempotency_key=str(uuid.uuid4()),
            payment_intents=[generate_payment_intent(cart_payment_id=cart_payment.id)],
            amount=875,
            client_description=None,
        )
        assert result_cart_payment
        assert result_cart_payment.amount == 875

    @pytest.mark.asyncio
    @pytest.mark.skip("Not yet implemented")
    async def test_add_amount_to_cart_payment_resubmit(self, cart_payment_interface):
        # TODO
        pass

    @pytest.mark.asyncio
    async def test_submit_amount_decrease_to_cart_payment(self, cart_payment_interface):
        cart_payment = generate_cart_payment(amount=600)
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, amount=600
        )

        result_intent, result_pgp_intent = await cart_payment_interface._submit_amount_decrease_to_cart_payment(
            cart_payment=cart_payment, payment_intent=payment_intent, amount=300
        )

        # Ensure amount changes, but state does not
        expected_intent_status = payment_intent.status
        assert result_intent
        assert result_intent.amount == 300
        assert result_intent.status == expected_intent_status

        assert result_pgp_intent
        assert result_pgp_intent.amount == 300
        assert result_pgp_intent.status == expected_intent_status

    @pytest.mark.asyncio
    async def test_deduct_amount_from_cart_payment_pending_capture(
        self, cart_payment_interface
    ):
        cart_payment = generate_cart_payment(amount=500)
        payment_intents = [
            generate_payment_intent(
                cart_payment_id=cart_payment.id, status="requires_capture"
            )
        ]
        updated_amount = 300

        result_cart_payment = await cart_payment_interface._deduct_amount_from_cart_payment(
            cart_payment=cart_payment,
            idempotency_key=str(uuid.uuid4()),
            payment_intents=payment_intents,
            amount=updated_amount,
            client_description=None,
        )

        assert result_cart_payment
        assert result_cart_payment.amount == updated_amount

    @pytest.mark.asyncio
    async def test_deduct_amount_from_cart_payment_post_capture(
        self, cart_payment_interface
    ):
        cart_payment = generate_cart_payment(amount=500)
        payment_intents = [generate_payment_intent(status="succeeded")]
        updated_amount = 300

        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[
                generate_pgp_payment_intent(
                    payment_intent_id=payment_intents[0].id, status="succeeded"
                )
            ]
        )

        result_cart_payment = await cart_payment_interface._deduct_amount_from_cart_payment(
            cart_payment=cart_payment,
            idempotency_key=str(uuid.uuid4()),
            payment_intents=payment_intents,
            amount=updated_amount,
            client_description=None,
        )

        assert result_cart_payment
        assert result_cart_payment.amount == updated_amount

    @pytest.mark.asyncio
    async def test_deduct_amount_from_cart_payment_post_capture_not_refundable(
        self, cart_payment_interface
    ):
        cart_payment = generate_cart_payment(amount=500)
        payment_intents = [generate_payment_intent(status="failed")]
        updated_amount = 900

        cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[generate_pgp_payment_intent("failed")]
        )

        with pytest.raises(PaymentIntentRefundError) as refund_error:
            await cart_payment_interface._deduct_amount_from_cart_payment(
                cart_payment=cart_payment,
                idempotency_key=str(uuid.uuid4()),
                payment_intents=payment_intents,
                amount=updated_amount,
                client_description=None,
            )
        assert (
            refund_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
        )

    @pytest.mark.asyncio
    @pytest.mark.skip("Not yet implemented")
    async def test_update_payment(self, cart_payment_interface):
        # TODO
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip("Not yet implemented")
    async def test_get_required_payment_resource_ids(self, cart_payment_interface):
        # TODO
        pass


class TestCapturePayment:
    @pytest.mark.asyncio
    async def test_cannot_acquire_lock(
        self, cart_payment_interface: CartPaymentInterface
    ):
        payment_intent = PaymentIntentFactory(status=IntentStatus.REQUIRES_CAPTURE)
        cart_payment_interface.payment_repo.update_payment_intent_status = (  # type: ignore
            MagicMock()
        )
        cart_payment_interface.payment_repo.update_payment_intent_status.side_effect = (  # type: ignore
            PaymentIntentCouldNotBeUpdatedError()
        )
        with pytest.raises(PaymentIntentConcurrentAccessError):
            await cart_payment_interface.capture_payment(payment_intent)

    @pytest.mark.asyncio
    async def test_success(self, cart_payment_interface: CartPaymentInterface):
        payment_intent = PaymentIntentFactory(
            status=IntentStatus.REQUIRES_CAPTURE
        )  # type: PaymentIntent
        cart_payment_interface.payment_repo.update_payment_intent = (  # type: ignore
            asynctest.CoroutineMock()
        )
        cart_payment_interface.payment_repo.update_payment_intent_status = (  # type: ignore
            asynctest.CoroutineMock()
        )
        cart_payment_interface.payment_repo.update_payment_intent_status.return_value = (  # type: ignore
            payment_intent
        )
        cart_payment_interface._capture_payment_with_provider = create_autospec(  # type: ignore
            cart_payment_interface._capture_payment_with_provider
        )
        pgp_payment_intent = PgpPaymentIntentFactory()  # type: PgpPaymentIntent
        cart_payment_interface.payment_repo.find_pgp_payment_intents = (  # type: ignore
            asynctest.CoroutineMock()
        )
        cart_payment_interface.payment_repo.find_pgp_payment_intents.return_value = [  # type: ignore
            pgp_payment_intent
        ]
        await cart_payment_interface.capture_payment(payment_intent)
        cart_payment_interface._capture_payment_with_provider.assert_called_once_with(  # type: ignore
            payment_intent, pgp_payment_intent
        )
