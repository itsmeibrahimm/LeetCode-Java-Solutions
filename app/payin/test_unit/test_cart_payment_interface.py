import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import asynctest
import pytest
from asynctest import create_autospec
from freezegun import freeze_time
from stripe.error import InvalidRequestError, StripeError

from app.commons.core.errors import DBOperationError
from app.commons.providers.errors import StripeCommandoError
from app.commons.providers.stripe.stripe_models import (
    StripeCreatePaymentIntentRequest,
    PaymentMethod as StripePaymentMethod,
)
from app.commons.types import CountryCode, Currency, LegacyCountryId, PgpCode
from app.payin.conftest import PaymentIntentFactory, PgpPaymentIntentFactory
from app.payin.core.cart_payment.model import (
    CartPayment,
    LegacyConsumerCharge,
    LegacyStripeCharge,
    PaymentCharge,
    PaymentIntent,
    PgpPaymentCharge,
    PgpPaymentIntent,
    SplitPayment,
    CartPaymentList,
)
from app.payin.core.cart_payment.processor import IdempotencyKeyAction
from app.payin.core.cart_payment.types import (
    CaptureMethod,
    ChargeStatus,
    IntentStatus,
    LegacyConsumerChargeId,
    LegacyStripeChargeStatus,
    RefundStatus,
)
from app.payin.core.exceptions import (
    CartPaymentCreateError,
    InvalidProviderRequestError,
    PayinErrorCode,
    PaymentChargeRefundError,
    PaymentIntentCancelError,
    PaymentIntentConcurrentAccessError,
    PaymentIntentCouldNotBeUpdatedError,
    ProviderError,
    ProviderPaymentIntentUnexpectedStatusError,
    CartPaymentUpdateError,
    LegacyStripeChargeConcurrentAccessError,
    LegacyStripeChargeUpdateError,
    LegacyStripeChargeCouldNotBeUpdatedError,
)
from app.payin.core.payer.types import DeletePayerRedactingText
from app.payin.core.payment_method.types import PgpPaymentInfo, CartPaymentSortKey
from app.payin.core.types import PgpPayerResourceId, PgpPaymentMethodResourceId
from app.payin.tests.utils import (
    FunctionMock,
    generate_cart_payment,
    generate_legacy_consumer_charge,
    generate_legacy_payment,
    generate_legacy_stripe_charge,
    generate_payment_intent,
    generate_payment_intent_adjustment_history,
    generate_pgp_payment_intent,
    generate_pgp_refund,
    generate_provider_charges,
    generate_provider_intent,
    generate_refund,
)


class TestLegacyPaymentInterface:
    """
    Test LegacyPaymentInterface class functions.
    """

    def test_get_legacy_stripe_charge_status_from_provider_status(
        self, legacy_payment_interface
    ):
        legacy_status = legacy_payment_interface._get_legacy_stripe_charge_status_from_provider_status(
            "succeeded"
        )
        assert legacy_status == LegacyStripeChargeStatus.SUCCEEDED

        with pytest.raises(ValueError):
            legacy_payment_interface._get_legacy_stripe_charge_status_from_provider_status(
                "coffee_beans"
            )

    @pytest.mark.asyncio
    async def test_get_legacy_consumer_charge_ids_by_consumer_id(
        self, legacy_payment_interface
    ):
        legacy_consumer_charge = generate_legacy_consumer_charge()

        legacy_payment_interface.payment_repo.get_legacy_consumer_charge_ids_by_consumer_id = FunctionMock(
            return_value=[legacy_consumer_charge.id]
        )
        result = await legacy_payment_interface.get_legacy_consumer_charge_ids_by_consumer_id(
            1
        )
        assert len(result) == 1
        assert result[0] == legacy_consumer_charge.id

    @pytest.mark.asyncio
    async def test_get_legacy_stripe_charges_by_charge_id(
        self, legacy_payment_interface
    ):
        legacy_consumer_charge = generate_legacy_consumer_charge()
        legacy_stripe_charge = generate_legacy_stripe_charge(
            charge_id=legacy_consumer_charge.id
        )

        legacy_payment_interface.payment_repo.get_legacy_stripe_charges_by_charge_id = FunctionMock(
            return_value=[legacy_stripe_charge]
        )
        result = await legacy_payment_interface.get_legacy_stripe_charges_by_charge_id(
            legacy_consumer_charge.id
        )
        assert len(result) == 1
        assert result[0] == legacy_stripe_charge

    @pytest.mark.asyncio
    async def test_update_legacy_stripe_charge_remove_pii(
        self, legacy_payment_interface
    ):
        legacy_stripe_charge = generate_legacy_stripe_charge()
        legacy_stripe_charge.description = DeletePayerRedactingText.REDACTED

        legacy_payment_interface.payment_repo.update_legacy_stripe_charge_remove_pii = FunctionMock(
            return_value=legacy_stripe_charge
        )
        result = await legacy_payment_interface.update_legacy_stripe_charge_remove_pii(
            legacy_stripe_charge.id
        )
        assert result == legacy_stripe_charge

    @pytest.mark.asyncio
    async def test_update_legacy_stripe_charge_remove_pii_none_found(
        self, legacy_payment_interface
    ):
        legacy_payment_interface.payment_repo.update_legacy_stripe_charge_remove_pii = FunctionMock(
            return_value=None
        )
        result = await legacy_payment_interface.update_legacy_stripe_charge_remove_pii(
            1
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_legacy_stripe_charge_remove_pii_errors(
        self, legacy_payment_interface
    ):
        legacy_stripe_charge = generate_legacy_stripe_charge()
        legacy_stripe_charge.description = DeletePayerRedactingText.REDACTED

        legacy_payment_interface.payment_repo.update_legacy_stripe_charge_remove_pii = FunctionMock(
            side_effect=DBOperationError(error_message="")
        )
        with pytest.raises(LegacyStripeChargeUpdateError) as e:
            await legacy_payment_interface.update_legacy_stripe_charge_remove_pii(
                legacy_stripe_charge.id
            )
        assert e.value.error_code == PayinErrorCode.LEGACY_STRIPE_CHARGE_UPDATE_DB_ERROR

    @pytest.mark.asyncio
    async def test_get_associated_cart_payment_id(self, legacy_payment_interface):
        cart_payment = generate_cart_payment()
        consumer_charge = generate_legacy_consumer_charge()
        legacy_payment_interface.payment_repo.get_payment_intent_by_legacy_consumer_charge_id_from_primary = FunctionMock(
            return_value=generate_payment_intent(cart_payment_id=cart_payment.id)
        )

        result = await legacy_payment_interface.get_associated_cart_payment_id(
            consumer_charge.id
        )
        assert result == cart_payment.id

    @pytest.mark.asyncio
    async def test_get_associated_cart_payment_id_no_match(
        self, legacy_payment_interface
    ):
        consumer_charge = generate_legacy_consumer_charge()
        legacy_payment_interface.payment_repo.get_payment_intent_by_legacy_consumer_charge_id_from_primary = FunctionMock(
            return_value=None
        )

        result = await legacy_payment_interface.get_associated_cart_payment_id(
            consumer_charge.id
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_find_existing_payment_charge(self, legacy_payment_interface):
        consumer_charge = generate_legacy_consumer_charge()
        idempotency_key = str(uuid.uuid4())

        legacy_payment_interface.payment_repo.get_legacy_stripe_charges_by_charge_id = FunctionMock(
            return_value=(
                [generate_legacy_stripe_charge(idempotency_key=idempotency_key)]
            )
        )

        result_consumer_charge, result_stripe_charge = await legacy_payment_interface.find_existing_payment_charge(
            consumer_charge.id, idempotency_key
        )
        assert result_consumer_charge
        assert type(result_consumer_charge) == LegacyConsumerCharge
        assert result_stripe_charge
        assert type(result_stripe_charge) == LegacyStripeCharge

    @pytest.mark.asyncio
    async def test_find_existing_payment_charge_no_match(
        self, legacy_payment_interface
    ):
        consumer_charge = generate_legacy_consumer_charge()
        legacy_payment_interface.payment_repo.get_legacy_consumer_charge_by_id = FunctionMock(
            return_value=None
        )

        result = await legacy_payment_interface.find_existing_payment_charge(
            consumer_charge.id, str(uuid.uuid4())
        )
        assert result == (None, None)

    @pytest.mark.asyncio
    async def test_insert_new_stripe_charge(self, legacy_payment_interface):
        result = await legacy_payment_interface._insert_new_stripe_charge(
            charge_id=1,
            amount=200,
            currency=Currency.USD,
            idempotency_key="id-key",
            description="test_description",
            card_id=5,
            additional_payment_info=None,
        )

        expected_legacy_stripe_charge = LegacyStripeCharge(
            id=result.id,  # generated
            amount=200,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.PENDING,
            error_reason="",
            additional_payment_info=None,
            description="test_description",
            idempotency_key="id-key",
            card_id=5,
            charge_id=1,
            stripe_id="",
            created_at=result.created_at,  # generated
            updated_at=result.updated_at,  # generated
            refunded_at=None,
        )

        assert result == expected_legacy_stripe_charge

    @pytest.mark.asyncio
    async def test_create_new_payment_charges(
        self, cart_payment_interface, legacy_payment_interface
    ):
        cart_payment = generate_cart_payment()
        legacy_payment = generate_legacy_payment()
        payment_intent = generate_payment_intent()

        result_consumer_charge, result_stripe_charge = await legacy_payment_interface.create_new_payment_charges(
            request_cart_payment=cart_payment,
            legacy_payment=legacy_payment,
            correlation_ids=cart_payment.correlation_ids,
            country=CountryCode(payment_intent.country),
            currency=Currency(payment_intent.currency),
            idempotency_key=payment_intent.idempotency_key,
        )

        expected_consumer_charge = LegacyConsumerCharge(
            id=result_consumer_charge.id,  # Generated
            target_id=int(cart_payment.correlation_ids.reference_id),
            target_ct_id=int(cart_payment.correlation_ids.reference_type),
            idempotency_key=payment_intent.idempotency_key,
            is_stripe_connect_based=False,
            total=0,
            original_total=cart_payment.amount,
            currency=Currency(payment_intent.currency),
            country_id=LegacyCountryId.US,
            issue_id=None,
            stripe_customer_id=None,
            updated_at=result_consumer_charge.updated_at,  # Generated
            created_at=result_consumer_charge.created_at,  # Generated
        )
        assert result_consumer_charge == expected_consumer_charge

        expected_stripe_charge = LegacyStripeCharge(
            id=result_stripe_charge.id,  # Generated
            amount=cart_payment.amount,
            amount_refunded=0,
            currency=Currency(payment_intent.currency),
            status=LegacyStripeChargeStatus.PENDING,
            error_reason="",
            additional_payment_info=str(legacy_payment.dd_additional_payment_info),
            description=cart_payment.client_description,
            idempotency_key=payment_intent.idempotency_key,
            card_id=legacy_payment.dd_stripe_card_id,
            charge_id=1,
            stripe_id=result_stripe_charge.stripe_id,
            created_at=result_stripe_charge.created_at,  # Generated
            updated_at=result_stripe_charge.updated_at,  # Generated
            refunded_at=None,
        )
        assert result_stripe_charge == expected_stripe_charge

    @pytest.mark.asyncio
    async def test_update_existing_payment_charge(
        self, cart_payment_interface, legacy_payment_interface
    ):
        legacy_consumer_charge = generate_legacy_consumer_charge()
        legacy_stripe_charge = generate_legacy_stripe_charge(
            charge_id=legacy_consumer_charge.id, stripe_id="test"
        )
        legacy_payment = generate_legacy_payment()
        payment_intent = generate_payment_intent(status="requires_capture", amount=490)

        result_stripe_charge = await legacy_payment_interface.update_existing_payment_charge(
            charge_id=legacy_consumer_charge.id,
            amount=payment_intent.amount,
            currency=payment_intent.currency,
            idempotency_key=payment_intent.idempotency_key,
            description="Test description",
            legacy_payment=legacy_payment,
        )

        expected_stripe_charge = LegacyStripeCharge(
            id=legacy_stripe_charge.id,
            amount=payment_intent.amount,  # Generate funtion uses amount from this object
            amount_refunded=legacy_stripe_charge.amount_refunded,
            currency=payment_intent.currency,
            status=LegacyStripeChargeStatus.PENDING,
            error_reason="",
            additional_payment_info=str(legacy_payment.dd_additional_payment_info),
            description="Test description",
            idempotency_key=result_stripe_charge.idempotency_key,  # Generated by mock function
            card_id=result_stripe_charge.card_id,  # Generated by mock function
            charge_id=legacy_stripe_charge.id,
            stripe_id="",
            created_at=result_stripe_charge.created_at,  # Generated
            updated_at=result_stripe_charge.updated_at,  # Generated
            refunded_at=None,
        )
        assert result_stripe_charge == expected_stripe_charge

    @pytest.mark.asyncio
    async def test_update_state_after_provider_submission(
        self, cart_payment_interface, legacy_payment_interface
    ):
        legacy_consumer_charge = generate_legacy_consumer_charge()
        legacy_stripe_charge = generate_legacy_stripe_charge()
        payment_intent = generate_payment_intent(status="requires_capture", amount=490)
        pgp_payment_intent = generate_pgp_payment_intent(
            status="requires_capture", payment_intent_id=payment_intent.id
        )
        provider_intent = generate_provider_intent()
        provider_intent.charges = generate_provider_charges(
            payment_intent, pgp_payment_intent
        )

        original_stripe_charge = deepcopy(legacy_stripe_charge)
        result_stripe_charge = await legacy_payment_interface.update_state_after_provider_submission(
            legacy_stripe_charge=legacy_stripe_charge,
            idempotency_key=payment_intent.idempotency_key,
            provider_payment_intent=provider_intent,
        )

        expected_stripe_charge = LegacyStripeCharge(
            id=original_stripe_charge.id,
            amount=pgp_payment_intent.amount,  # Generate funtion uses amount from this object
            amount_refunded=original_stripe_charge.amount_refunded,
            currency=original_stripe_charge.currency,
            status="succeeded",
            error_reason=original_stripe_charge.error_reason,
            additional_payment_info=original_stripe_charge.error_reason,
            description=original_stripe_charge.description,
            idempotency_key=result_stripe_charge.idempotency_key,  # Generated by mock function
            card_id=result_stripe_charge.card_id,  # Generated by mock function
            charge_id=legacy_consumer_charge.id,
            stripe_id=result_stripe_charge.stripe_id,
            created_at=result_stripe_charge.created_at,  # Generated
            updated_at=result_stripe_charge.updated_at,  # Generated
            refunded_at=None,
        )
        assert result_stripe_charge == expected_stripe_charge

    @pytest.mark.asyncio
    async def test_update_legacy_charge_after_capture(
        self, cart_payment_interface, legacy_payment_interface
    ):
        payment_intent = generate_payment_intent(status="requires_capture")
        pgp_payment_intent = generate_pgp_payment_intent(
            status="requires_capture", payment_intent_id=payment_intent.id
        )
        provider_intent = generate_provider_intent()
        provider_intent.charges = generate_provider_charges(
            payment_intent, pgp_payment_intent
        )

        result_stripe_charge = await legacy_payment_interface.update_charge_after_payment_captured(
            provider_intent
        )
        assert result_stripe_charge
        assert result_stripe_charge.status == "succeeded"

    @pytest.mark.asyncio
    async def test_legacy_lower_amount_for_uncaptured_payment(
        self, cart_payment_interface, legacy_payment_interface
    ):
        stripe_id = "test_stripe_id"
        amount_refunded = 570
        result_stripe_charge = await legacy_payment_interface.lower_amount_for_uncaptured_payment(
            stripe_id=stripe_id, amount_refunded=amount_refunded
        )

        assert result_stripe_charge
        assert result_stripe_charge.amount_refunded == amount_refunded
        assert result_stripe_charge.refunded_at

    @pytest.mark.asyncio
    async def test_update_legacy_charge_after_payment_cancelled(
        self, cart_payment_interface, legacy_payment_interface
    ):
        payment_intent = generate_payment_intent(status="requires_capture")
        pgp_payment_intent = generate_pgp_payment_intent(
            status="requires_capture", payment_intent_id=payment_intent.id
        )
        provider_intent = generate_provider_intent(amount_refunded=500)
        provider_intent.charges = generate_provider_charges(
            payment_intent, pgp_payment_intent, 500
        )

        result_stripe_charge = await legacy_payment_interface.update_charge_after_payment_cancelled(
            provider_intent
        )
        assert result_stripe_charge
        assert result_stripe_charge.amount_refunded == 500
        assert result_stripe_charge.refunded_at

    @pytest.mark.asyncio
    async def test_update_legacy_charge_after_refund(
        self, cart_payment_interface, legacy_payment_interface
    ):
        provider_refund = (
            await cart_payment_interface.app_context.stripe.refund_charge()
        )
        result_stripe_charge = await legacy_payment_interface.update_charge_after_payment_refunded(
            provider_refund
        )

        assert result_stripe_charge
        assert result_stripe_charge.amount_refunded == provider_refund.amount
        assert result_stripe_charge.refunded_at

    @pytest.mark.asyncio
    async def test_extract_error_reason_from_exception(self, legacy_payment_interface):
        # Use provider decline code if it is provided
        exception = CartPaymentCreateError(
            error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_DECLINED_ERROR,
            provider_charge_id=str(uuid.uuid4()),
            provider_error_code="card_declined",
            provider_decline_code="generic_decline",
            has_provider_error_details=True,
        )
        assert (
            legacy_payment_interface._extract_error_reason_from_exception(exception)
            == "generic_decline"
        )

        # If no decline code, use provider error code
        exception = CartPaymentCreateError(
            error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_DECLINED_ERROR,
            provider_charge_id=str(uuid.uuid4()),
            provider_error_code="card_declined",
            provider_decline_code=None,
            has_provider_error_details=True,
        )
        assert (
            legacy_payment_interface._extract_error_reason_from_exception(exception)
            == "card_declined"
        )

        # Error details exist but not specific fields like error_code, and error happened from calling provider
        exception = CartPaymentCreateError(
            error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR,
            provider_charge_id=None,
            provider_error_code=None,
            provider_decline_code=None,
            has_provider_error_details=True,
        )
        assert (
            legacy_payment_interface._extract_error_reason_from_exception(exception)
            == "empty_error_reason"
        )

        # No error details, but error from calling provider
        exception = CartPaymentCreateError(
            error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR,
            provider_charge_id=None,
            provider_error_code=None,
            provider_decline_code=None,
            has_provider_error_details=False,
        )
        assert (
            legacy_payment_interface._extract_error_reason_from_exception(exception)
            == "generic_stripe_api_error"
        )

        # Error but not from calling provider
        exception = CartPaymentCreateError(
            error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_ERROR,
            provider_charge_id=None,
            provider_error_code=None,
            provider_decline_code=None,
            has_provider_error_details=False,
        )
        assert (
            legacy_payment_interface._extract_error_reason_from_exception(exception)
            == "generic_exception"
        )

    @pytest.mark.asyncio
    async def test_mark_charge_as_failed_generic_message(
        self, cart_payment_interface, legacy_payment_interface
    ):
        legacy_stripe_charge = generate_legacy_stripe_charge()
        result = await legacy_payment_interface.mark_charge_as_failed(
            stripe_charge=legacy_stripe_charge,
            creation_exception=CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_ERROR,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            ),
        )
        assert result.status == LegacyStripeChargeStatus.FAILED
        assert result.stripe_id.startswith("stripeid_lost_")
        assert result.error_reason == "generic_exception"

    @pytest.mark.asyncio
    async def test_mark_charge_as_failed_error_code_message(
        self, cart_payment_interface, legacy_payment_interface
    ):
        legacy_stripe_charge = generate_legacy_stripe_charge()
        stripe_id = str(uuid.uuid4())
        result = await legacy_payment_interface.mark_charge_as_failed(
            stripe_charge=legacy_stripe_charge,
            creation_exception=CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR,
                provider_charge_id=stripe_id,
                provider_error_code="card declined",
                provider_decline_code=None,
                has_provider_error_details=False,
            ),
        )
        assert result.status == LegacyStripeChargeStatus.FAILED
        assert result.stripe_id == stripe_id
        assert result.error_reason == "card declined"

    @pytest.mark.asyncio
    async def test_mark_charge_as_failed_decline_code_message(
        self, cart_payment_interface, legacy_payment_interface
    ):
        legacy_stripe_charge = generate_legacy_stripe_charge()
        result = await legacy_payment_interface.mark_charge_as_failed(
            stripe_charge=legacy_stripe_charge,
            creation_exception=CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR,
                provider_charge_id=None,
                provider_error_code="card_declined",
                provider_decline_code="generic_decline",
                has_provider_error_details=False,
            ),
        )
        assert result.status == LegacyStripeChargeStatus.FAILED
        assert result.stripe_id.startswith("stripeid_lost_")
        assert result.error_reason == "generic_decline"

    @pytest.mark.asyncio
    async def test_mark_charge_as_failed_empty_error_reason_message(
        self, cart_payment_interface, legacy_payment_interface
    ):
        legacy_stripe_charge = generate_legacy_stripe_charge()
        result = await legacy_payment_interface.mark_charge_as_failed(
            stripe_charge=legacy_stripe_charge,
            creation_exception=CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=True,
            ),
        )
        assert result.status == LegacyStripeChargeStatus.FAILED
        assert result.stripe_id.startswith("stripeid_lost_")
        assert result.error_reason == "empty_error_reason"

    @pytest.mark.asyncio
    async def test_mark_charge_as_failed_generic_stripe_message(
        self, cart_payment_interface, legacy_payment_interface
    ):
        legacy_stripe_charge = generate_legacy_stripe_charge()
        result = await legacy_payment_interface.mark_charge_as_failed(
            stripe_charge=legacy_stripe_charge,
            creation_exception=CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            ),
        )
        assert result.status == LegacyStripeChargeStatus.FAILED
        assert result.stripe_id.startswith("stripeid_lost_")
        assert result.error_reason == "generic_stripe_api_error"

    @pytest.mark.asyncio
    async def test_mark_charge_as_failed_record_not_updated(
        self, cart_payment_interface, legacy_payment_interface
    ):
        legacy_stripe_charge = generate_legacy_stripe_charge()
        legacy_payment_interface.payment_repo.update_legacy_stripe_charge_error_details = FunctionMock(
            side_effect=LegacyStripeChargeCouldNotBeUpdatedError()
        )
        with pytest.raises(LegacyStripeChargeConcurrentAccessError) as e:
            await legacy_payment_interface.mark_charge_as_failed(
                stripe_charge=legacy_stripe_charge,
                creation_exception=CartPaymentCreateError(
                    error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR,
                    provider_charge_id=None,
                    provider_error_code=None,
                    provider_decline_code=None,
                    has_provider_error_details=False,
                ),
            )
        assert e.value.error_code == PayinErrorCode.CART_PAYMENT_CONCURRENT_ACCESS_ERROR


class TestCartPaymentInterface:
    """
    Test CartPaymentInterface class functions.
    """

    @pytest.mark.asyncio
    async def test_update_cart_payments_remove_pii(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.client_description = DeletePayerRedactingText.REDACTED

        cart_payment_interface.payment_repo.update_cart_payments_remove_pii = FunctionMock(
            return_value=[cart_payment]
        )
        results = await cart_payment_interface.update_cart_payments_remove_pii(1)
        assert len(results) == 1
        assert results[0] == cart_payment

    @pytest.mark.asyncio
    async def test_update_cart_payments_remove_pii_errors(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.client_description = DeletePayerRedactingText.REDACTED

        cart_payment_interface.payment_repo.update_cart_payments_remove_pii = FunctionMock(
            side_effect=DBOperationError(error_message="")
        )
        with pytest.raises(CartPaymentUpdateError) as e:
            await cart_payment_interface.update_cart_payments_remove_pii(1)
        assert e.value.error_code == PayinErrorCode.CART_PAYMENT_UPDATE_DB_ERROR

    def test_enable_new_charge_tables(self, cart_payment_interface):
        # We expect new charge table use to be disabled on launch of payment service
        assert cart_payment_interface.ENABLE_NEW_CHARGE_TABLES is False

    def test_get_idempotency_key_for_provider_call(self, cart_payment_interface):
        client_key = "client_key"
        idempotency_key = cart_payment_interface.get_idempotency_key_for_provider_call(
            client_key=client_key, action=IdempotencyKeyAction.CREATE
        )
        assert idempotency_key == f"{client_key}-{IdempotencyKeyAction.CREATE.value}"

    @pytest.mark.asyncio
    async def test_get_most_recent_intent(self, cart_payment_interface):
        first_intent = generate_payment_intent()
        second_intent = generate_payment_intent()

        result = cart_payment_interface.get_most_recent_intent(
            [first_intent, second_intent]
        )
        assert result == second_intent

    @pytest.mark.asyncio
    async def test_get_most_recent_pgp_payment_intent(self, cart_payment_interface):
        first_pgp_intent = generate_pgp_payment_intent()
        second_pgp_intent = generate_pgp_payment_intent()

        cart_payment_interface.payment_repo.list_pgp_payment_intents_from_primary = FunctionMock(
            return_value=[first_pgp_intent, second_pgp_intent]
        )

        result = await cart_payment_interface._get_most_recent_pgp_payment_intent(
            MagicMock()
        )
        assert result == second_pgp_intent

    @pytest.mark.asyncio
    async def test_get_cart_payment_submission_pgp_intent(self, cart_payment_interface):
        first_intent = generate_pgp_payment_intent(status="init")
        second_intent = generate_pgp_payment_intent(status="init")
        pgp_intents = [first_intent, second_intent]
        cart_payment_interface.payment_repo.list_pgp_payment_intents_from_primary = FunctionMock(
            return_value=pgp_intents
        )
        selected_intent = await cart_payment_interface.get_cart_payment_submission_pgp_intent(
            generate_payment_intent()
        )
        assert selected_intent == first_intent

    def test_filter_for_payment_intent_by_state(self, cart_payment_interface):
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
        result = cart_payment_interface.filter_payment_intents_by_idempotency_key(
            intents, target_intent.idempotency_key
        )
        assert result == target_intent

        result = cart_payment_interface.filter_payment_intents_by_idempotency_key(
            intents, f"{target_intent.idempotency_key}-fake"
        )
        assert result is None

    def test_get_capturable_payment_intents(self, cart_payment_interface):
        payment_intents = [
            generate_payment_intent(status=IntentStatus.INIT),
            generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE),
            generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE),
            generate_payment_intent(status=IntentStatus.SUCCEEDED),
            generate_payment_intent(status=IntentStatus.FAILED),
        ]

        result = cart_payment_interface.get_capturable_payment_intents(payment_intents)
        assert result == [payment_intents[1], payment_intents[2]]

    def test_get_refundable_payment_intents(self, cart_payment_interface):
        payment_intents = [
            generate_payment_intent(status=IntentStatus.INIT),
            generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE),
            generate_payment_intent(status=IntentStatus.SUCCEEDED),
            generate_payment_intent(status=IntentStatus.FAILED),
        ]

        result = cart_payment_interface.get_refundable_payment_intents(payment_intents)
        assert result == [payment_intents[2]]

    def test_filter_payment_intents_by_function(self, cart_payment_interface):
        target_payment_intent = generate_payment_intent()
        second_intent = generate_payment_intent()

        def filter_function(payment_intent: PaymentIntent) -> bool:
            return payment_intent.id == target_payment_intent.id

        result = cart_payment_interface._filter_payment_intents_by_function(
            [target_payment_intent, second_intent], filter_function
        )
        assert result == [target_payment_intent]

    def test_is_payment_intent_submitted(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.INIT.value)
        assert cart_payment_interface.is_payment_intent_submitted(intent) is False

        intent = generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE.value)
        assert cart_payment_interface.is_payment_intent_submitted(intent) is True

        intent = generate_payment_intent(status=IntentStatus.SUCCEEDED.value)
        assert cart_payment_interface.is_payment_intent_submitted(intent) is True

        intent = generate_payment_intent(status=IntentStatus.FAILED.value)
        assert cart_payment_interface.is_payment_intent_submitted(intent) is False

        intent = generate_payment_intent(status=IntentStatus.PENDING.value)
        assert cart_payment_interface.is_payment_intent_submitted(intent) is False

    def test_is_payment_intent_failed(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.INIT.value)
        assert cart_payment_interface.is_payment_intent_failed(intent) is False

        intent = generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE.value)
        assert cart_payment_interface.is_payment_intent_failed(intent) is False

        intent = generate_payment_intent(status=IntentStatus.SUCCEEDED.value)
        assert cart_payment_interface.is_payment_intent_failed(intent) is False

        intent = generate_payment_intent(status=IntentStatus.FAILED.value)
        assert cart_payment_interface.is_payment_intent_failed(intent) is True

        intent = generate_payment_intent(status=IntentStatus.PENDING.value)
        assert cart_payment_interface.is_payment_intent_failed(intent) is False

    def test_can_payment_intent_be_cancelled(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.FAILED)
        assert cart_payment_interface.can_payment_intent_be_cancelled(intent) is False

        intent = generate_payment_intent(status=IntentStatus.SUCCEEDED)
        assert cart_payment_interface.can_payment_intent_be_cancelled(intent) is False

        intent = generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)
        assert cart_payment_interface.can_payment_intent_be_cancelled(intent) is True

    def test_can_payment_intent_be_refunded(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.FAILED)
        assert cart_payment_interface.can_payment_intent_be_refunded(intent) is False

        intent = generate_payment_intent(status=IntentStatus.SUCCEEDED)
        assert cart_payment_interface.can_payment_intent_be_refunded(intent) is True

        intent = generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)
        assert cart_payment_interface.can_payment_intent_be_refunded(intent) is False

        intent = generate_payment_intent(status=IntentStatus.SUCCEEDED, amount=0)
        assert cart_payment_interface.can_payment_intent_be_refunded(intent) is False

    def test_get_intent_status_from_provider_status(self, cart_payment_interface):
        intent_status = cart_payment_interface._get_intent_status_from_provider_status(
            "requires_capture"
        )
        assert intent_status == IntentStatus.REQUIRES_CAPTURE

        with pytest.raises(ValueError):
            cart_payment_interface._get_intent_status_from_provider_status(
                "coffee_beans"
            )

    def test_get_refund_status_from_provider_refund(self, cart_payment_interface):
        refund_status = cart_payment_interface._get_refund_status_from_provider_refund(
            "pending"
        )
        assert refund_status == RefundStatus.PROCESSING

        refund_status = cart_payment_interface._get_refund_status_from_provider_refund(
            "succeeded"
        )
        assert refund_status == RefundStatus.SUCCEEDED

        refund_status = cart_payment_interface._get_refund_status_from_provider_refund(
            "failed"
        )
        assert refund_status == RefundStatus.FAILED

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

    def test_is_update_cancelling_payment(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        assert (
            cart_payment_interface.is_amount_adjustment_cancelling_payment(
                cart_payment, 0
            )
            is True
        )
        assert (
            cart_payment_interface.is_amount_adjustment_cancelling_payment(
                cart_payment, 100
            )
            is False
        )

    def test_is_amount_adjusted_higher(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.amount = 500

        assert (
            cart_payment_interface.is_amount_adjusted_higher(cart_payment, 400) is False
        )
        assert (
            cart_payment_interface.is_amount_adjusted_higher(cart_payment, 500) is False
        )
        assert (
            cart_payment_interface.is_amount_adjusted_higher(cart_payment, 600) is True
        )

    def test_is_amount_adjusted_lower(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.amount = 500

        assert (
            cart_payment_interface.is_amount_adjusted_lower(cart_payment, 400) is True
        )
        assert (
            cart_payment_interface.is_amount_adjusted_lower(cart_payment, 500) is False
        )
        assert (
            cart_payment_interface.is_amount_adjusted_lower(cart_payment, 600) is False
        )

    def test_is_refund_ended(self, cart_payment_interface):
        refund = generate_refund(status=RefundStatus.PROCESSING)
        result = cart_payment_interface.is_refund_ended(refund)
        assert result is False

        refund = generate_refund(status=RefundStatus.SUCCEEDED)
        result = cart_payment_interface.is_refund_ended(refund)
        assert result is True

        refund = generate_refund(status=RefundStatus.FAILED)
        result = cart_payment_interface.is_refund_ended(refund)
        assert result is True

    def test_transform_method_for_stripe(self, cart_payment_interface):
        assert (
            cart_payment_interface._transform_method_for_stripe("auto") == "automatic"
        )
        assert cart_payment_interface._transform_method_for_stripe("manual") == "manual"

    def test_get_provider_capture_method(self, cart_payment_interface):
        intent = generate_payment_intent(capture_method="manual")
        result = cart_payment_interface._get_provider_capture_method(intent)
        assert result == StripeCreatePaymentIntentRequest.CaptureMethod.MANUAL

        intent = generate_payment_intent(capture_method="auto")
        result = cart_payment_interface._get_provider_capture_method(intent)
        assert result == StripeCreatePaymentIntentRequest.CaptureMethod.AUTOMATIC

    def test_get_provider_future_usage(self, cart_payment_interface):
        intent = generate_payment_intent(capture_method="manual")
        result = cart_payment_interface._get_provider_future_usage(intent)
        assert result == StripeCreatePaymentIntentRequest.SetupFutureUsage.OFF_SESSION

        intent = generate_payment_intent(capture_method="auto")
        result = cart_payment_interface._get_provider_future_usage(intent)
        assert result == StripeCreatePaymentIntentRequest.SetupFutureUsage.ON_SESSION

    @pytest.mark.asyncio
    async def test_find_existing_payment_no_matches(self, cart_payment_interface):
        mock_intent_search = FunctionMock(return_value=None)
        cart_payment_interface.payment_repo.get_payment_intent_by_idempotency_key_from_primary = (
            mock_intent_search
        )
        result = await cart_payment_interface.find_existing_payment(
            payer_id="payer_id", idempotency_key="idempotency_key"
        )
        assert result == (None, None, None)

    @pytest.mark.asyncio
    async def test_find_existing_payment_with_matches(self, cart_payment_interface):
        # Mock function to find intent
        intent = generate_payment_intent()
        cart_payment_interface.payment_repo.get_payment_intent_by_idempotency_key_from_primary = FunctionMock(
            return_value=intent
        )

        # Mock function to find cart payment
        cart_payment = MagicMock()
        legacy_payment = MagicMock()
        cart_payment_interface.payment_repo.get_cart_payment_by_id_from_primary = FunctionMock(
            return_value=(cart_payment, legacy_payment)
        )

        result = await cart_payment_interface.find_existing_payment(
            payer_id="payer_id", idempotency_key="idempotency_key"
        )
        assert result == (cart_payment, legacy_payment, intent)

    @pytest.mark.asyncio
    async def test_get_cart_payment_with_match(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment_interface.payment_repo.get_cart_payment_by_id_from_primary = FunctionMock(
            return_value=cart_payment
        )

        result = await cart_payment_interface.get_cart_payment(cart_payment.id)
        assert result == cart_payment

    @pytest.mark.asyncio
    async def test_get_cart_payment_no_match(self, cart_payment_interface):
        cart_payment_interface.payment_repo.get_cart_payment_by_id_from_primary = FunctionMock(
            return_value=None
        )

        result = await cart_payment_interface.get_cart_payment(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cart_payment_intents(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        # Mocked db function returns a single match
        result = await cart_payment_interface.get_cart_payment_intents(cart_payment)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_payment_intent_adjustment(self, cart_payment_interface):
        cart_payment_interface.payment_repo.get_payment_intent_adjustment_history_from_primary = FunctionMock(
            return_value=None
        )
        result = await cart_payment_interface.get_payment_intent_adjustment(
            idempotency_key=str(uuid.uuid4())
        )
        assert result is None

        history_record = generate_payment_intent_adjustment_history()
        cart_payment_interface.payment_repo.get_payment_intent_adjustment_history_from_primary = FunctionMock(
            return_value=history_record
        )
        result = await cart_payment_interface.get_payment_intent_adjustment(
            idempotency_key=str(uuid.uuid4())
        )
        assert result == history_record

    @pytest.mark.asyncio
    async def test_find_existing_refund(self, cart_payment_interface):
        result = await cart_payment_interface.find_existing_refund(str(uuid.uuid4()))
        assert result == (None, None)

        refund = generate_refund()
        pgp_refund = generate_pgp_refund()
        cart_payment_interface.payment_repo.get_refund_by_idempotency_key_from_primary = FunctionMock(
            return_value=refund
        )
        cart_payment_interface.payment_repo.get_pgp_refund_by_refund_id_from_primary = FunctionMock(
            return_value=pgp_refund
        )
        result_refund, result_pgp_refund = await cart_payment_interface.find_existing_refund(
            str(uuid.uuid4())
        )
        assert result_refund == refund
        assert result_pgp_refund == pgp_refund

    def test_is_adjustment_for_payment_intents(self, cart_payment_interface):
        payment_intent = generate_payment_intent()
        adjustment_history = generate_payment_intent_adjustment_history(
            payment_intent_id=payment_intent.id
        )

        result = cart_payment_interface.is_adjustment_for_payment_intents(
            adjustment_history=adjustment_history, intent_list=[payment_intent]
        )
        assert result is True

        result = cart_payment_interface.is_adjustment_for_payment_intents(
            adjustment_history=adjustment_history,
            intent_list=[generate_payment_intent()],
        )
        assert result is False

    def test_is_accessible(self, cart_payment_interface):
        # Stub function: return value is fixed
        assert (
            cart_payment_interface.is_accessible(
                cart_payment=generate_cart_payment(),
                request_payer_id="payer_id",
                credential_owner="credential_ower",
            )
            is True
        )

    @pytest.mark.asyncio
    @freeze_time("2011-01-01")
    async def test_create_new_payment(self, cart_payment_interface, stripe_interface):
        # Parameters for function
        request_cart_payment = generate_cart_payment(
            capture_method=CaptureMethod.MANUAL.value
        )
        legacy_payment = generate_legacy_payment()
        payment_resource_id = "payment_resource_id"
        customer_resource_id = "customer_resource_id"
        idempotency_key = str(uuid.uuid4())
        country = "US"
        currency = "USD"
        result_cart_payment, result_payment_intent, result_pgp_payment_intent = await cart_payment_interface.create_new_payment(
            request_cart_payment=request_cart_payment,
            legacy_payment=legacy_payment,
            legacy_consumer_charge_id=LegacyConsumerChargeId(9999),
            provider_payment_method_id=payment_resource_id,
            provider_customer_resource_id=customer_resource_id,
            provider_metadata=None,
            idempotency_key=idempotency_key,
            country=country,
            currency=currency,
        )

        expected_cart_payment = deepcopy(request_cart_payment)
        # Fill in generated fields
        expected_cart_payment.payment_method_id = (
            None
        )  # populate_cart_payment_for_response not called yet
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
            application_fee_amount=None,
            capture_method=CaptureMethod.MANUAL.value,
            country=country,
            currency=currency,
            status=IntentStatus.INIT,
            statement_descriptor=None,
            payment_method_id=request_cart_payment.payment_method_id,
            created_at=result_payment_intent.created_at,  # Generated field
            updated_at=result_payment_intent.updated_at,  # Generated field
            captured_at=None,
            cancelled_at=None,
            legacy_consumer_charge_id=LegacyConsumerChargeId(9999),
        )
        assert result_payment_intent
        assert result_payment_intent == expected_payment_intent
        assert result_payment_intent.id
        assert result_payment_intent.created_at
        assert result_payment_intent.updated_at
        assert not result_payment_intent.capture_after

        # TODO check pgp_payment_intent as well

    @pytest.mark.asyncio
    async def test_create_new_charge_pair(self, cart_payment_interface):
        payment_intent = generate_payment_intent()
        pgp_payment_intent = generate_pgp_payment_intent()

        provider_intent = generate_provider_intent()
        provider_intent.charges = generate_provider_charges(
            payment_intent, pgp_payment_intent
        )

        result_payment_charge, result_pgp_charge = await cart_payment_interface._create_new_charge_pair(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_intent=provider_intent,
            status=ChargeStatus.SUCCEEDED,
        )

        expected_payment_charge = PaymentCharge(
            id=result_payment_charge.id,  # Generated
            payment_intent_id=payment_intent.id,
            pgp_code=pgp_payment_intent.pgp_code,
            idempotency_key=result_payment_charge.idempotency_key,
            status=ChargeStatus.SUCCEEDED,
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
            pgp_code=pgp_payment_intent.pgp_code,
            idempotency_key=result_payment_charge.idempotency_key,
            status=ChargeStatus.SUCCEEDED,
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
    async def test_create_new_intent_pair(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        result_intent, result_pgp_intent = await cart_payment_interface._create_new_intent_pair(
            cart_payment_id=cart_payment.id,
            idempotency_key="idempotency_key",
            payment_method_id=cart_payment.payment_method_id,
            provider_payment_method_id="provider_payment_method_id",
            provider_customer_resource_id="provider_customer_resource_id",
            provider_metadata={"is_first_order": False},
            amount=cart_payment.amount,
            country="US",
            currency="USD",
            split_payment=cart_payment.split_payment,
            capture_method=CaptureMethod.MANUAL,
            payer_statement_description=None,
            legacy_consumer_charge_id=LegacyConsumerChargeId(560),
        )

        expected_payment_intent = PaymentIntent(
            id=result_intent.id,  # Generated field
            cart_payment_id=cart_payment.id,
            idempotency_key="idempotency_key",
            amount_initiated=cart_payment.amount,
            amount=cart_payment.amount,
            application_fee_amount=None,
            capture_method="manual",
            country="US",
            currency="USD",
            status=IntentStatus.INIT,
            statement_descriptor=None,
            payment_method_id=cart_payment.payment_method_id,
            metadata={"is_first_order": False},
            legacy_consumer_charge_id=LegacyConsumerChargeId(560),
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
            pgp_code=PgpCode.STRIPE,
            status=IntentStatus.INIT,
            resource_id=None,
            charge_resource_id=None,
            invoice_resource_id=None,
            payment_method_resource_id="provider_payment_method_id",
            customer_resource_id="provider_customer_resource_id",
            currency="USD",
            amount=cart_payment.amount,
            amount_capturable=None,
            amount_received=None,
            application_fee_amount=None,
            capture_method="manual",
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
        assert not result_intent.capture_after

    @pytest.mark.asyncio
    async def test_clone_payment_method(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.INIT.value)
        mocked_payment_method = create_autospec(StripePaymentMethod)
        mocked_payment_method.id = "cloned_payment_method_id"
        cart_payment_interface.stripe_async_client.clone_payment_method = FunctionMock(
            return_value=mocked_payment_method
        )
        provider_payment_method_id = await cart_payment_interface._clone_payment_method(
            payment_intent_id=intent.id,
            provider_payment_method_id="payment_resource_id",
            provider_customer_id="customer_resource_id",
            source_country=CountryCode.CA,
            destination_country=CountryCode.US,
        )
        assert provider_payment_method_id == "cloned_payment_method_id"

    @pytest.mark.asyncio
    async def test_clone_payment_method_errors(self, cart_payment_interface):
        # StripeError case
        intent = generate_payment_intent(status=IntentStatus.INIT.value)
        cart_payment_interface.stripe_async_client.clone_payment_method = FunctionMock(
            side_effect=StripeError()
        )
        with pytest.raises(CartPaymentCreateError) as e:
            await cart_payment_interface._clone_payment_method(
                payment_intent_id=intent.id,
                provider_payment_method_id="payment_resource_id",
                provider_customer_id="customer_resource_id",
                source_country=CountryCode.CA,
                destination_country=CountryCode.US,
            )
        assert (
            e.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_CREATE_CROSS_COUNTRY_PAYMENT_METHOD_ERROR
        )

        # General exception case
        cart_payment_interface.stripe_async_client.clone_payment_method = FunctionMock(
            side_effect=Exception()
        )
        with pytest.raises(CartPaymentCreateError) as e:
            await cart_payment_interface._clone_payment_method(
                payment_intent_id=intent.id,
                provider_payment_method_id="payment_resource_id",
                provider_customer_id="customer_resource_id",
                source_country=CountryCode.CA,
                destination_country=CountryCode.US,
            )
        assert e.value.error_code == PayinErrorCode.PAYMENT_INTENT_CREATE_ERROR

    @pytest.mark.asyncio
    async def test_submit_payment_to_provider(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        pgp_payment_info = PgpPaymentInfo(
            pgp_payer_resource_id=PgpPayerResourceId("customer_resource_id"),
            pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                "payment_resource_id"
            ),
        )
        response = await cart_payment_interface.submit_payment_to_provider(
            payer_country=CountryCode.US,
            payment_intent=intent,
            pgp_payment_intent=pgp_intent,
            pgp_payment_info=pgp_payment_info,
            provider_description="test_description",
        )
        name, args, kwargs = cart_payment_interface.stripe_async_client.create_payment_intent.mock_calls[
            0
        ]
        assert kwargs
        assert kwargs.get("request", None)
        assert kwargs["request"].metadata
        assert kwargs["request"].metadata.get("payment_intent_id", None)
        assert kwargs["request"].metadata.get("payment_intent_id", None) == str(
            intent.id
        )
        assert response

    @pytest.mark.asyncio
    async def test_submit_commando_payment_to_provider(self, cart_payment_interface):
        mocked_create_payment_intent = MagicMock()
        mocked_create_payment_intent.side_effect = StripeCommandoError
        cart_payment_interface.stripe_async_client.create_payment_intent = (
            mocked_create_payment_intent
        )
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        pgp_payment_info = PgpPaymentInfo(
            pgp_payer_resource_id=PgpPayerResourceId("customer_resource_id"),
            pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                "payment_resource_id"
            ),
        )
        cart_payment_interface.req_context.verify_card_in_commando_mode = False
        response = await cart_payment_interface.submit_payment_to_provider(
            payer_country=CountryCode.US,
            payment_intent=intent,
            pgp_payment_intent=pgp_intent,
            pgp_payment_info=pgp_payment_info,
            provider_description="test_description",
        )
        assert response
        assert response.status == IntentStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_submit_commando_payment_to_provider_verify_card_failed(
        self, cart_payment_interface, runtime_setter
    ):
        mocked_create_payment_intent = MagicMock()
        mocked_create_payment_intent.side_effect = StripeCommandoError
        cart_payment_interface.stripe_async_client.create_payment_intent = (
            mocked_create_payment_intent
        )
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        pgp_payment_info = PgpPaymentInfo(
            pgp_payer_resource_id=PgpPayerResourceId("customer_resource_id"),
            pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                "payment_resource_id"
            ),
        )

        mocked_is_card_verified = FunctionMock(return_value=False)
        cart_payment_interface._is_card_verified = mocked_is_card_verified

        with pytest.raises(CartPaymentCreateError):
            await cart_payment_interface.submit_payment_to_provider(
                payer_country=CountryCode.US,
                payment_intent=intent,
                pgp_payment_intent=pgp_intent,
                pgp_payment_info=pgp_payment_info,
                provider_description="test_description",
            )

    @pytest.mark.asyncio
    async def test_commando_mode_verify_card(
        self, cart_payment_interface, runtime_setter
    ):
        mocked_is_stripe_card_valid_and_has_success_charge_record = FunctionMock()
        cart_payment_interface.payment_repo.is_stripe_card_valid_and_has_success_charge_record = (
            mocked_is_stripe_card_valid_and_has_success_charge_record
        )

        cart_payment_interface.req_context.verify_card_in_commando_mode = False
        mocked_is_stripe_card_valid_and_has_success_charge_record.return_value = False
        assert await cart_payment_interface._is_card_verified(MagicMock())

        mocked_is_stripe_card_valid_and_has_success_charge_record.return_value = True
        assert await cart_payment_interface._is_card_verified(MagicMock())

        cart_payment_interface.req_context.verify_card_in_commando_mode = True
        mocked_is_stripe_card_valid_and_has_success_charge_record.return_value = False
        assert not await cart_payment_interface._is_card_verified(MagicMock())

        mocked_is_stripe_card_valid_and_has_success_charge_record.return_value = True
        assert await cart_payment_interface._is_card_verified(MagicMock())

    @pytest.mark.asyncio
    async def test_submit_payment_to_provider_error(self, cart_payment_interface):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = StripeError()
        cart_payment_interface.app_context.stripe.create_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        pgp_payment_info = PgpPaymentInfo(
            pgp_payer_resource_id=PgpPayerResourceId("customer_resource_id"),
            pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                "payment_resource_id"
            ),
        )

        with pytest.raises(CartPaymentCreateError) as payment_error:
            await cart_payment_interface.submit_payment_to_provider(
                payer_country=CountryCode.US,
                payment_intent=intent,
                pgp_payment_intent=pgp_intent,
                pgp_payment_info=pgp_payment_info,
                provider_description="test_description",
            )
        name, args, kwargs = cart_payment_interface.stripe_async_client.create_payment_intent.mock_calls[
            0
        ]
        assert kwargs
        assert kwargs.get("request", None)
        assert kwargs["request"].metadata
        assert kwargs["request"].metadata.get("payment_intent_id", None)
        assert kwargs["request"].metadata.get("payment_intent_id", None) == str(
            intent.id
        )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR
        )

    @pytest.mark.asyncio
    async def test_update_payment_after_submission_to_provider_from_init_to_requires_capture(
        self, cart_payment_interface
    ):
        now = datetime.utcnow()
        created_at = now.astimezone(timezone.utc) - timedelta(days=5)

        intent = generate_payment_intent(status="init", created_at=created_at)
        pgp_intent = generate_pgp_payment_intent(status="init", created_at=created_at)
        pgp_payment_info = PgpPaymentInfo(
            pgp_payer_resource_id=PgpPayerResourceId("customer_resource_id"),
            pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                "payment_resource_id"
            ),
        )
        provider_intent = await cart_payment_interface.submit_payment_to_provider(
            payer_country=CountryCode.US,
            payment_intent=intent,
            pgp_payment_intent=pgp_intent,
            pgp_payment_info=pgp_payment_info,
            provider_description="test_description",
        )

        assert intent.status != IntentStatus.REQUIRES_CAPTURE
        assert not intent.capture_after
        with freeze_time(now):  # freeze time to make updated capture_after predictable
            result_intent, result_pgp_intent = await cart_payment_interface.update_payment_after_submission_to_provider(
                intent, pgp_intent, provider_intent
            )

        assert result_intent.status == IntentStatus.REQUIRES_CAPTURE
        assert result_intent.capture_after == now + timedelta(
            minutes=cart_payment_interface.capture_service.default_capture_delay_in_minutes
        )
        assert result_pgp_intent.status == IntentStatus.REQUIRES_CAPTURE

    @pytest.mark.asyncio
    async def test_acquire_for_capture(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        result = await cart_payment_interface.acquire_for_capture(intent)
        assert result.status == IntentStatus.CAPTURING

    @pytest.mark.asyncio
    async def test_cancel_provider_payment_charge(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        response = await cart_payment_interface.cancel_provider_payment_charge(
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
            await cart_payment_interface.cancel_provider_payment_charge(
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
        refund = generate_refund()
        response = await cart_payment_interface.refund_provider_payment(
            refund=refund,
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
        refund = generate_refund()

        with pytest.raises(PaymentIntentCancelError) as payment_error:
            await cart_payment_interface.refund_provider_payment(
                refund=refund,
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
    async def test_update_pgp_charge_from_provider(self, cart_payment_interface):
        provider_intent = generate_provider_intent()
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
    async def test_update_charge_pair_after_capture(self, cart_payment_interface):
        payment_intent = generate_payment_intent(status="requires_capture")
        pgp_payment_intent = generate_pgp_payment_intent(
            status="requires_capture", payment_intent_id=payment_intent.id
        )
        provider_intent = generate_provider_intent()
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
    @pytest.mark.skip("Not yet implemented")
    async def test_get_pgp_payment_method_by_legacy_payment(
        self, cart_payment_interface
    ):
        # TODO
        pass

    @pytest.mark.asyncio
    async def test_update_payment_after_cancel_with_provider(
        self, cart_payment_interface
    ):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        provider_intent = generate_provider_intent()
        provider_intent.charges = generate_provider_charges(intent, pgp_intent)
        result_intent, result_pgp_intent = await cart_payment_interface.update_payment_after_cancel_with_provider(
            payment_intent=intent,
            pgp_payment_intent=pgp_intent,
            provider_payment_intent=provider_intent,
        )

        assert result_intent
        assert result_intent.status == IntentStatus.CANCELLED

        assert result_pgp_intent
        assert result_pgp_intent.status == IntentStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_create_new_refund(self, cart_payment_interface):
        cart_payment = generate_cart_payment(amount=600)
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, amount=cart_payment.amount
        )

        idempotency_key = str(uuid.uuid4())
        result_refund, result_pgp_refund = await cart_payment_interface.create_new_refund(
            refund_amount=200,
            cart_payment=cart_payment,
            payment_intent=payment_intent,
            idempotency_key=idempotency_key,
        )
        assert result_refund.idempotency_key == idempotency_key
        assert result_refund.status == RefundStatus.PROCESSING
        assert result_refund.amount == 200

        assert result_pgp_refund.refund_id == result_refund.id
        assert result_pgp_refund.idempotency_key == idempotency_key
        assert result_pgp_refund.status == RefundStatus.PROCESSING
        assert result_pgp_refund.amount == 200

    @pytest.mark.asyncio
    async def test_update_payment_after_refund_with_provider(
        self, cart_payment_interface
    ):
        payment_intent = generate_payment_intent(status=IntentStatus.SUCCEEDED)
        pgp_payment_intent = generate_pgp_payment_intent(
            payment_intent_id=payment_intent.id, status=IntentStatus.SUCCEEDED
        )
        refund = generate_refund()
        pgp_refund = generate_pgp_refund()

        provider_refund = (
            await cart_payment_interface.app_context.stripe.refund_charge()
        )

        result_payment_intent = await cart_payment_interface.update_payment_after_refund_with_provider(
            refund_amount=100,
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            refund=refund,
            pgp_refund=pgp_refund,
            provider_refund=provider_refund,
        )
        assert result_payment_intent.amount == payment_intent.amount - 100

    @pytest.mark.asyncio
    async def test_increase_payment_amount(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id,
            legacy_consumer_charge_id=LegacyConsumerChargeId(7888),
        )
        result_intent, result_pgp_intent = await cart_payment_interface.increase_payment_amount(
            cart_payment=cart_payment,
            existing_payment_intents=[payment_intent],
            idempotency_key=str(uuid.uuid4()),
            amount=875,
            split_payment=None,
        )
        assert result_intent.amount == 875
        assert (
            result_intent.legacy_consumer_charge_id
            == payment_intent.legacy_consumer_charge_id
        )
        assert result_intent.application_fee_amount is None
        assert result_pgp_intent.payout_account_id is None

    @pytest.mark.asyncio
    async def test_increase_payment_amount_with_split_payment(
        self, cart_payment_interface
    ):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id,
            legacy_consumer_charge_id=LegacyConsumerChargeId(7888),
        )
        result_intent, result_pgp_intent = await cart_payment_interface.increase_payment_amount(
            cart_payment=cart_payment,
            existing_payment_intents=[payment_intent],
            idempotency_key=str(uuid.uuid4()),
            amount=875,
            split_payment=SplitPayment(
                payout_account_id="test_merchant_account", application_fee_amount=75
            ),
        )
        assert result_intent.amount == 875
        assert (
            result_intent.legacy_consumer_charge_id
            == payment_intent.legacy_consumer_charge_id
        )
        assert result_intent.application_fee_amount == 75
        assert result_pgp_intent.payout_account_id == "test_merchant_account"

    @pytest.mark.asyncio
    async def test_lower_amount_for_uncaptured_payment(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        payment_intent = generate_payment_intent()
        result_intent = await cart_payment_interface.lower_amount_for_uncaptured_payment(
            cart_payment=cart_payment,
            payment_intent=payment_intent,
            amount=200,
            idempotency_key=str(uuid.uuid4()),
        )
        assert result_intent.amount == 200

    @pytest.mark.asyncio
    async def test_mark_payment_as_failed(self, cart_payment_interface):
        intent = generate_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)
        pgp_intent = generate_pgp_payment_intent(status=IntentStatus.REQUIRES_CAPTURE)

        result_intent, result_pgp_intent = await cart_payment_interface.mark_payment_as_failed(
            intent, pgp_intent
        )
        assert result_intent.status == IntentStatus.FAILED
        assert result_pgp_intent.status == IntentStatus.FAILED

    def verify_populate_cart_payment_for_response(
        self,
        response_cart_payment: CartPayment,
        original_cart_payment: CartPayment,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
    ):
        # Fields populated based on related objects
        assert (
            response_cart_payment.payment_method_id == payment_intent.payment_method_id
        )
        assert (
            response_cart_payment.payer_statement_description
            == payment_intent.statement_descriptor
        )

        if (
            payment_intent.application_fee_amount
            and pgp_payment_intent.payout_account_id
        ):
            assert response_cart_payment.split_payment == SplitPayment(
                payout_account_id=pgp_payment_intent.payout_account_id,
                application_fee_amount=payment_intent.application_fee_amount,
            )
        else:
            assert response_cart_payment.split_payment is None

        # Unchanged attributes
        assert response_cart_payment.id == original_cart_payment.id
        assert response_cart_payment.amount == original_cart_payment.amount
        assert response_cart_payment.payer_id == original_cart_payment.payer_id
        assert (
            response_cart_payment.correlation_ids
            == original_cart_payment.correlation_ids
        )
        assert response_cart_payment.created_at == original_cart_payment.created_at
        assert (
            response_cart_payment.delay_capture == original_cart_payment.delay_capture
        )
        assert response_cart_payment.updated_at == original_cart_payment.updated_at
        assert response_cart_payment.deleted_at == original_cart_payment.deleted_at
        assert (
            response_cart_payment.client_description
            == original_cart_payment.client_description
        )

    def test_populate_cart_payment_for_response(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cart_payment.delay_capture = True
        cart_payment.payer_statement_description = "Fill in here"
        intent = generate_payment_intent(
            status="requires_capture", capture_method="auto"
        )
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        original_cart_payment = deepcopy(cart_payment)
        cart_payment_interface.populate_cart_payment_for_response(
            cart_payment, intent, pgp_intent
        )
        self.verify_populate_cart_payment_for_response(
            cart_payment, original_cart_payment, intent, pgp_intent
        )

    def test_populate_cart_payment_for_response_with_split_payment(
        self, cart_payment_interface
    ):
        cart_payment = generate_cart_payment()
        cart_payment.delay_capture = True
        cart_payment.payer_statement_description = "Fill in here"
        intent = generate_payment_intent(
            status="requires_capture", capture_method="auto", application_fee_amount=30
        )
        pgp_intent = generate_pgp_payment_intent(payout_account_id="test_account_id")

        original_cart_payment = deepcopy(cart_payment)
        cart_payment_interface.populate_cart_payment_for_response(
            cart_payment, intent, pgp_intent
        )
        self.verify_populate_cart_payment_for_response(
            cart_payment, original_cart_payment, intent, pgp_intent
        )

    @pytest.mark.asyncio
    async def test_update_cart_payment_attributes(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        result = await cart_payment_interface.update_cart_payment_attributes(
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
    async def test_update_cart_payment_post_deletion(self, cart_payment_interface):
        cart_payment = generate_cart_payment()
        cancelled_cart_payment = await cart_payment_interface.update_cart_payment_post_cancellation(
            id=cart_payment.id
        )
        assert cancelled_cart_payment
        assert cancelled_cart_payment.deleted_at is not None
        assert cancelled_cart_payment.updated_at is not None
        assert isinstance(cancelled_cart_payment.updated_at, datetime)
        assert isinstance(cancelled_cart_payment.deleted_at, datetime)


class TestCapturePayment:
    @pytest.mark.asyncio
    async def test_cannot_acquire_lock(self, cart_payment_processor):
        payment_intent = PaymentIntentFactory(status=IntentStatus.REQUIRES_CAPTURE)
        cart_payment_processor.cart_payment_interface.payment_repo.update_payment_intent = (  # type: ignore
            MagicMock()
        )
        cart_payment_processor.cart_payment_interface.payment_repo.update_payment_intent.side_effect = (
            # type: ignore
            PaymentIntentCouldNotBeUpdatedError()
        )
        with pytest.raises(PaymentIntentConcurrentAccessError):
            await cart_payment_processor.capture_payment(payment_intent)

    @pytest.mark.asyncio
    async def test_success(self, cart_payment_processor):
        payment_intent = PaymentIntentFactory(
            status=IntentStatus.REQUIRES_CAPTURE,
            capture_after=datetime.now() - timedelta(seconds=1),
        )  # type: PaymentIntent
        cart_payment_processor.cart_payment_interface.payment_repo.update_payment_intent = (  # type: ignore
            asynctest.CoroutineMock()
        )
        cart_payment_processor.cart_payment_interface.payment_repo.update_payment_intent = (  # type: ignore
            asynctest.CoroutineMock()
        )
        cart_payment_processor.cart_payment_interface.payment_repo.update_payment_intent.return_value = (
            # type: ignore
            payment_intent
        )
        cart_payment_processor.cart_payment_interface.submit_capture_to_provider = create_autospec(  # type: ignore
            cart_payment_processor.cart_payment_interface.submit_capture_to_provider
        )
        cart_payment_processor.cart_payment_interface._get_intent_status_from_provider_status = create_autospec(
            # type: ignore
            cart_payment_processor.cart_payment_interface._get_intent_status_from_provider_status,
            return_value=IntentStatus.SUCCEEDED,
        )
        cart_payment_processor.legacy_payment_interface.update_charge_after_payment_captured = (  # type: ignore
            asynctest.CoroutineMock()
        )
        pgp_payment_intent = PgpPaymentIntentFactory()  # type: PgpPaymentIntent
        cart_payment_processor.cart_payment_interface.payment_repo.list_pgp_payment_intents_from_primary = (  # type: ignore
            asynctest.CoroutineMock()
        )
        cart_payment_processor.cart_payment_interface.payment_repo.list_pgp_payment_intents_from_primary.return_value = [
            # type: ignore
            pgp_payment_intent
        ]
        await cart_payment_processor.capture_payment(payment_intent)
        cart_payment_processor.cart_payment_interface.submit_capture_to_provider.assert_called_once_with(
            # type: ignore
            payment_intent,
            pgp_payment_intent,
        )


class TestCapturePaymentWithProvider(object):
    @pytest.mark.asyncio
    async def test_capture_payment_partial(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture", amount=300)
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        response = await cart_payment_interface.submit_capture_to_provider(
            intent, pgp_intent
        )
        assert response.amount_received == intent.amount

    @pytest.mark.asyncio
    async def test_capture_payment_with_provider(self, cart_payment_interface):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")
        response = await cart_payment_interface.submit_capture_to_provider(
            intent, pgp_intent
        )
        assert response.amount_received == intent.amount

    @pytest.mark.asyncio
    async def test_capture_payment_with_generic_stripe_error(
        self, cart_payment_interface
    ):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = StripeError()
        cart_payment_interface.app_context.stripe.capture_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        with pytest.raises(ProviderError):
            await cart_payment_interface.submit_capture_to_provider(intent, pgp_intent)

    @pytest.mark.asyncio
    async def test_submit_capture_to_provider_unexpected_status_not_success_or_cancel(
        self, cart_payment_interface
    ):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = InvalidRequestError(
            "Payment intent already captured",
            "",
            code="payment_intent_unexpected_state",
            json_body={"error": {"payment_intent": {"status": "failed"}}},
        )
        cart_payment_interface.app_context.stripe.capture_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        with pytest.raises(InvalidProviderRequestError):
            await cart_payment_interface.submit_capture_to_provider(intent, pgp_intent)

    @pytest.mark.asyncio
    async def test_submit_capture_to_provider_unexpected_status_success_or_cancel(
        self, cart_payment_interface
    ):
        mocked_stripe_function = FunctionMock()
        mocked_stripe_function.side_effect = InvalidRequestError(
            "Payment intent already captured",
            "",
            code="payment_intent_unexpected_state",
            json_body={"error": {"payment_intent": {"status": "canceled"}}},
        )
        cart_payment_interface.app_context.stripe.capture_payment_intent = (
            mocked_stripe_function
        )

        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        with pytest.raises(ProviderPaymentIntentUnexpectedStatusError) as info:
            await cart_payment_interface.submit_capture_to_provider(intent, pgp_intent)
        error = info.value
        assert isinstance(error, ProviderPaymentIntentUnexpectedStatusError)
        assert error.pgp_payment_intent_status == pgp_intent.status
        assert error.provider_payment_intent_status == "canceled"
        assert isinstance(error.orig_error, InvalidRequestError)

        mocked_stripe_function.side_effect = InvalidRequestError(
            "Payment intent already captured",
            "",
            code="payment_intent_unexpected_state",
            json_body={"error": {"payment_intent": {"status": "succeeded"}}},
        )
        with pytest.raises(ProviderPaymentIntentUnexpectedStatusError) as info:
            await cart_payment_interface.submit_capture_to_provider(intent, pgp_intent)
        error = info.value
        assert isinstance(error, ProviderPaymentIntentUnexpectedStatusError)
        assert error.pgp_payment_intent_status == pgp_intent.status
        assert error.provider_payment_intent_status == "succeeded"
        assert isinstance(error.orig_error, InvalidRequestError)

    @pytest.mark.asyncio
    async def test_update_payment_after_capture_with_provider(
        self, cart_payment_interface
    ):
        intent = generate_payment_intent(status="requires_capture")
        pgp_intent = generate_pgp_payment_intent(status="requires_capture")

        provider_intent = await cart_payment_interface.submit_capture_to_provider(
            intent, pgp_intent
        )
        provider_intent.amount_received = 750
        provider_intent.amount_capturable = 0
        provider_intent.status = "succeeded"

        result_intent, result_pgp_intent = await cart_payment_interface.update_payment_after_capture_with_provider(
            intent, pgp_intent, provider_intent
        )
        assert result_pgp_intent.amount_received == provider_intent.amount_received
        assert result_pgp_intent.amount_capturable == provider_intent.amount_capturable
        assert result_pgp_intent.status == IntentStatus.SUCCEEDED


class TestListCartPayment(object):
    @pytest.mark.asyncio
    async def test_get_cart_payment_list_by_dd_consumer_id(
        self, legacy_payment_interface
    ):
        cart_payment = generate_cart_payment()
        legacy_payment_interface.payment_repo.get_cart_payments_by_dd_consumer_id = FunctionMock(
            return_value=[cart_payment]
        )
        cart_payment_list = await legacy_payment_interface.list_cart_payments_by_dd_consumer_id(
            dd_consumer_id=1,
            created_at_gte=None,
            created_at_lte=None,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert cart_payment_list
        assert isinstance(cart_payment_list, CartPaymentList)
        assert cart_payment_list.count
        assert cart_payment_list.count == 1
        assert cart_payment_list.has_more is False
        assert cart_payment_list.data
        assert cart_payment_list.data[0] == cart_payment

    @pytest.mark.asyncio
    async def test_get_cart_payment_list__by_dd_consumer_id_sort_order(
        self, legacy_payment_interface
    ):
        now = datetime.now(timezone.utc)
        cart_payment_1 = generate_cart_payment(created_at=now)
        cart_payment_2 = generate_cart_payment(created_at=now + timedelta(minutes=1))
        legacy_payment_interface.payment_repo.get_cart_payments_by_dd_consumer_id = FunctionMock(
            return_value=[cart_payment_1, cart_payment_2]
        )
        cart_payment_list = await legacy_payment_interface.list_cart_payments_by_dd_consumer_id(
            dd_consumer_id=1,
            created_at_gte=None,
            created_at_lte=None,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert cart_payment_list
        assert isinstance(cart_payment_list, CartPaymentList)
        assert cart_payment_list.count == 2
        assert cart_payment_list.has_more is False
        assert cart_payment_1 in cart_payment_list.data
        assert cart_payment_2 in cart_payment_list.data
        assert cart_payment_list.data.index(
            cart_payment_1
        ) < cart_payment_list.data.index(cart_payment_2)

    @pytest.mark.asyncio
    async def test_get_cart_payment_list_by_dd_consumer_id_with_created_at_gte(
        self, legacy_payment_interface
    ):
        now = datetime.now(timezone.utc)
        cart_payment_1 = generate_cart_payment(created_at=now)
        cart_payment_2 = generate_cart_payment(created_at=now - timedelta(minutes=1))
        legacy_payment_interface.payment_repo.get_cart_payments_by_dd_consumer_id = FunctionMock(
            return_value=[cart_payment_1, cart_payment_2]
        )
        cart_payment_list = await legacy_payment_interface.list_cart_payments_by_dd_consumer_id(
            dd_consumer_id=1,
            created_at_gte=now,
            created_at_lte=None,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert cart_payment_list
        assert isinstance(cart_payment_list, CartPaymentList)
        assert cart_payment_list.count == 1
        assert cart_payment_list.has_more is False
        assert cart_payment_1 in cart_payment_list.data
        assert cart_payment_2 not in cart_payment_list.data

    @pytest.mark.asyncio
    async def test_get_cart_payment_list_by_dd_consumer_id_with_created_at_lte(
        self, legacy_payment_interface
    ):
        now = datetime.now(timezone.utc)
        cart_payment_1 = generate_cart_payment(created_at=now)
        cart_payment_2 = generate_cart_payment(created_at=now + timedelta(minutes=1))
        legacy_payment_interface.payment_repo.get_cart_payments_by_dd_consumer_id = FunctionMock(
            return_value=[cart_payment_1, cart_payment_2]
        )
        cart_payment_list = await legacy_payment_interface.list_cart_payments_by_dd_consumer_id(
            dd_consumer_id=1,
            created_at_gte=None,
            created_at_lte=now,
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert cart_payment_list
        assert isinstance(cart_payment_list, CartPaymentList)
        assert cart_payment_list.count == 1
        assert cart_payment_list.has_more is False
        assert cart_payment_1 in cart_payment_list.data
        assert cart_payment_2 not in cart_payment_list.data

    @pytest.mark.asyncio
    async def test_get_cart_payment_list_by_dd_consumer_id_with_created_at_gte_and_created_at_lte(
        self, legacy_payment_interface
    ):
        now = datetime.now(timezone.utc)
        cart_payment_1 = generate_cart_payment(created_at=now)
        cart_payment_2 = generate_cart_payment(created_at=now + timedelta(minutes=1))
        cart_payment_3 = generate_cart_payment(created_at=now - timedelta(minutes=1))
        cart_payment_4 = generate_cart_payment(created_at=now + timedelta(minutes=2))
        legacy_payment_interface.payment_repo.get_cart_payments_by_dd_consumer_id = FunctionMock(
            return_value=[
                cart_payment_1,
                cart_payment_2,
                cart_payment_3,
                cart_payment_4,
            ]
        )
        cart_payment_list = await legacy_payment_interface.list_cart_payments_by_dd_consumer_id(
            dd_consumer_id=1,
            created_at_gte=now,
            created_at_lte=now + timedelta(minutes=1),
            sort_by=CartPaymentSortKey.CREATED_AT,
        )
        assert cart_payment_list
        assert isinstance(cart_payment_list, CartPaymentList)
        assert cart_payment_list.count == 2
        assert cart_payment_list.has_more is False
        assert cart_payment_1 in cart_payment_list.data
        assert cart_payment_2 in cart_payment_list.data
        assert cart_payment_3 not in cart_payment_list.data
        assert cart_payment_4 not in cart_payment_list.data
