import uuid
from copy import deepcopy
import pytest

from app.commons.core.errors import DBOperationError
from app.commons.types import CountryCode, Currency, LegacyCountryId
from app.payin.core.cart_payment.model import LegacyConsumerCharge, LegacyStripeCharge
from app.payin.core.cart_payment.types import LegacyStripeChargeStatus
from app.payin.core.exceptions import (
    CartPaymentCreateError,
    PayinErrorCode,
    LegacyStripeChargeConcurrentAccessError,
    LegacyStripeChargeUpdateError,
    LegacyStripeChargeCouldNotBeUpdatedError,
)
from app.payin.core.payer.types import DeletePayerRedactingText
from app.payin.tests.utils import (
    FunctionMock,
    generate_cart_payment,
    generate_legacy_consumer_charge,
    generate_legacy_payment,
    generate_legacy_stripe_charge,
    generate_payment_intent,
    generate_pgp_payment_intent,
    generate_provider_charges,
    generate_provider_intent,
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
