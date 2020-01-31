from datetime import date, datetime, timedelta, timezone
from typing import cast, Optional, Tuple, List
from uuid import UUID, uuid4

import pytest
from IPython.utils.tz import utcnow

from app.commons.types import CountryCode, Currency, LegacyCountryId, PgpCode
from app.commons.utils.validation import not_none
from app.payin.core.cart_payment.model import (
    CartPayment,
    CorrelationIds,
    LegacyConsumerCharge,
    LegacyPayment,
    LegacyStripeCharge,
    PaymentCharge,
    PaymentIntent,
    PaymentIntentAdjustmentHistory,
    PgpPaymentCharge,
    PgpPaymentIntent,
    PgpRefund,
    Refund,
)
from app.payin.core.cart_payment.types import (
    CaptureMethod,
    ChargeStatus,
    IntentStatus,
    LegacyConsumerChargeId,
    LegacyStripeChargeStatus,
    RefundReason,
    RefundStatus,
)
from app.payin.core.exceptions import (
    LegacyStripeChargeCouldNotBeUpdatedError,
    PaymentIntentCouldNotBeUpdatedError,
)
from app.payin.core.payer.types import DeletePayerRedactingText
from app.payin.core.types import PayerReferenceIdType
from app.payin.core.types import PgpPayerResourceId, PgpPaymentMethodResourceId
from app.payin.models.paymentdb import cart_payments
from app.payin.repository.cart_payment_repo import (
    CartPaymentRepository,
    UpdateCartPaymentPostCancellationInput,
    UpdatePaymentIntentSetInput,
    UpdatePaymentIntentWhereInput,
    UpdatePgpPaymentIntentSetInput,
    UpdatePgpPaymentIntentWhereInput,
    GetCartPaymentsByConsumerIdInput,
    UpdateLegacyStripeChargeRemovePiiWhereInput,
    UpdateLegacyStripeChargeRemovePiiSetInput,
    UpdateCartPaymentsRemovePiiWhereInput,
    UpdateCartPaymentsRemovePiiSetInput,
    GetLegacyConsumerChargeIdsByConsumerIdInput,
    UpdateLegacyStripeChargeErrorDetailsWhereInput,
    UpdateLegacyStripeChargeErrorDetailsSetInput,
    ListCartPaymentsByReferenceId,
    GetCartPaymentsByReferenceId,
    GetConsumerChargeByReferenceId,
)
from app.payin.repository.payer_repo import (
    InsertPayerInput,
    PayerDbEntity,
    PayerRepository,
)
from app.payin.repository.payment_method_repo import (
    GetStripeCardByStripeIdInput,
    InsertPgpPaymentMethodInput,
    InsertStripeCardInput,
    PaymentMethodRepository,
    PgpPaymentMethodDbEntity,
    StripeCardDbEntity,
)


@pytest.fixture
async def payer(payer_repository: PayerRepository) -> PayerDbEntity:
    insert_payer_input = InsertPayerInput(
        id=uuid4(),
        payer_reference_id_type=PayerReferenceIdType.DD_DRIVE_STORE_ID,
        country=CountryCode.US,
    )
    return await payer_repository.insert_payer(insert_payer_input)


@pytest.fixture
async def payment_method(
    payer: PayerDbEntity, payment_method_repository: PaymentMethodRepository
) -> PgpPaymentMethodDbEntity:
    insert_payment_method = InsertPgpPaymentMethodInput(
        id=uuid4(),
        pgp_code=PgpCode.STRIPE,
        pgp_resource_id=str(uuid4()),
        payer_id=payer.id,
    )

    insert_stripe_card = InsertStripeCardInput(
        stripe_id=insert_payment_method.pgp_resource_id,
        fingerprint="fingerprint",
        last4="1500",
        dynamic_last4="1500",
        exp_month="9",
        exp_year="2024",
        type="mastercard",
        active=True,
    )
    insert_pm_result = await payment_method_repository.insert_pgp_payment_method(
        insert_payment_method
    )
    await payment_method_repository.insert_stripe_card(insert_stripe_card)

    return insert_pm_result


@pytest.fixture
async def stripe_card(
    payment_method: PgpPaymentMethodDbEntity,
    payment_method_repository: PaymentMethodRepository,
) -> StripeCardDbEntity:
    return not_none(
        await payment_method_repository.get_stripe_card_by_stripe_id(
            input=GetStripeCardByStripeIdInput(stripe_id=payment_method.pgp_resource_id)
        )
    )


@pytest.fixture
async def payment_method_expired(
    payer: PayerDbEntity, payment_method_repository: PaymentMethodRepository
) -> PgpPaymentMethodDbEntity:
    insert_payment_method = InsertPgpPaymentMethodInput(
        id=uuid4(),
        pgp_code=PgpCode.STRIPE,
        pgp_resource_id=str(uuid4()),
        payer_id=payer.id,
    )

    insert_stripe_card = InsertStripeCardInput(
        stripe_id=insert_payment_method.pgp_resource_id,
        fingerprint="fingerprint",
        last4="1500",
        dynamic_last4="1500",
        exp_month="1",
        exp_year="1990",
        type="mastercard",
        active=True,
    )
    insert_pm_result = await payment_method_repository.insert_pgp_payment_method(
        insert_payment_method
    )
    await payment_method_repository.insert_stripe_card(insert_stripe_card)

    return insert_pm_result


@pytest.fixture
async def stripe_card_expired(
    payment_method_expired: PgpPaymentMethodDbEntity,
    payment_method_repository: PaymentMethodRepository,
) -> StripeCardDbEntity:
    return not_none(
        await payment_method_repository.get_stripe_card_by_stripe_id(
            input=GetStripeCardByStripeIdInput(
                stripe_id=payment_method_expired.pgp_resource_id
            )
        )
    )


@pytest.fixture
async def cart_payment(
    cart_payment_repository: CartPaymentRepository, payer: PayerDbEntity
) -> CartPayment:
    return await cart_payment_repository.insert_cart_payment(
        id=uuid4(),
        payer_id=cast(UUID, payer.id),
        amount_original=99,
        amount_total=100,
        client_description="John Doe ordered donuts",
        reference_id="99",
        reference_type="88",
        delay_capture=False,
        metadata=None,
        legacy_consumer_id=1,
        legacy_stripe_card_id=1,
        legacy_provider_customer_id="stripe_customer_id",
        legacy_provider_card_id="stripe_card_id",
    )


async def create_payment_intent(
    cart_payment_repository: CartPaymentRepository,
    payer: PayerDbEntity,
    payment_method: PgpPaymentMethodDbEntity,
    payment_intent__capture_after,
    intent_status: IntentStatus = IntentStatus.REQUIRES_CAPTURE,
) -> PaymentIntent:
    cart_payment_id = uuid4()
    await cart_payment_repository.insert_cart_payment(
        id=cart_payment_id,
        payer_id=payer.id,
        amount_original=99,
        amount_total=100,
        client_description=None,
        reference_id="99",
        reference_type="88",
        legacy_consumer_id=None,
        delay_capture=False,
        metadata=None,
        legacy_stripe_card_id=1,
        legacy_provider_customer_id="stripe_customer_id",
        legacy_provider_card_id="stripe_card_id",
    )

    return await cart_payment_repository.insert_payment_intent(
        id=uuid4(),
        cart_payment_id=cart_payment_id,
        idempotency_key=f"ik_{uuid4()}",
        amount_initiated=100,
        amount=200,
        application_fee_amount=100,
        country=CountryCode.US,
        currency="USD",
        capture_method=CaptureMethod.MANUAL,
        status=intent_status,
        statement_descriptor=None,
        capture_after=payment_intent__capture_after,
        payment_method_id=payment_method.id,
        metadata={"is_first_order": True},
        legacy_consumer_charge_id=LegacyConsumerChargeId(11),
    )


@pytest.fixture
def payment_intent__capture_after() -> datetime:
    """
    Use to override the capture_after of payment_intent
    :return:
    """
    return datetime(2019, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
async def payment_intent(
    cart_payment_repository: CartPaymentRepository,
    payer: PayerDbEntity,
    payment_method: PgpPaymentMethodDbEntity,
    payment_intent__capture_after: datetime,
) -> PaymentIntent:
    return await create_payment_intent(
        cart_payment_repository, payer, payment_method, payment_intent__capture_after
    )


@pytest.fixture
async def pgp_payment_intent(
    cart_payment_repository: CartPaymentRepository, payment_intent: PaymentIntent
):
    yield await cart_payment_repository.insert_pgp_payment_intent(
        id=uuid4(),
        payment_intent_id=payment_intent.id,
        idempotency_key=str(uuid4()),
        pgp_code=PgpCode.STRIPE,
        payment_method_resource_id="pm_test",
        customer_resource_id=None,
        currency="USD",
        amount=500,
        application_fee_amount=None,
        payout_account_id=None,
        capture_method=CaptureMethod.MANUAL,
        status=IntentStatus.REQUIRES_CAPTURE,
        statement_descriptor="Test",
    )


@pytest.fixture
async def refund(
    cart_payment_repository: CartPaymentRepository, payment_intent: PaymentIntent
):
    yield await cart_payment_repository.insert_refund(
        id=uuid4(),
        payment_intent_id=payment_intent.id,
        idempotency_key=payment_intent.idempotency_key,
        status=RefundStatus.PROCESSING,
        amount=payment_intent.amount,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
    )


@pytest.fixture
async def pgp_refund(cart_payment_repository: CartPaymentRepository, refund: Refund):
    yield await cart_payment_repository.insert_pgp_refund(
        id=uuid4(),
        refund_id=refund.id,
        idempotency_key=refund.idempotency_key,
        status=RefundStatus.PROCESSING,
        amount=refund.amount,
        reason=RefundReason.REQUESTED_BY_CUSTOMER,
        pgp_code=PgpCode.STRIPE,
        pgp_resource_id=f"test-refund-{uuid4()}",
        pgp_charge_resource_id=f"test-charge-{uuid4()}",
    )


@pytest.fixture
async def payment_charge(
    cart_payment_repository: CartPaymentRepository, payment_intent: PaymentIntent
):
    yield await cart_payment_repository.insert_payment_charge(
        id=uuid4(),
        payment_intent_id=payment_intent.id,
        pgp_code=PgpCode.STRIPE,
        idempotency_key=str(uuid4()),
        status=ChargeStatus.REQUIRES_CAPTURE,
        currency="USD",
        amount=400,
        amount_refunded=0,
        application_fee_amount=None,
        payout_account_id=None,
    )


@pytest.fixture
async def pgp_payment_charge(
    cart_payment_repository: CartPaymentRepository, payment_charge: PaymentCharge
):
    yield await cart_payment_repository.insert_pgp_payment_charge(
        id=uuid4(),
        payment_charge_id=payment_charge.id,
        pgp_code=PgpCode.STRIPE,
        idempotency_key=str(uuid4()),
        status=ChargeStatus.REQUIRES_CAPTURE,
        currency="USD",
        amount=400,
        amount_refunded=0,
        application_fee_amount=None,
        payout_account_id=None,
        resource_id=None,
        intent_resource_id=str(uuid4()),
        invoice_resource_id=None,
        payment_method_resource_id=str(uuid4()),
    )


class TestPaymentIntent:
    @pytest.mark.asyncio
    async def test_get_payment_intent_by_id(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        retrieved_correct_payment_intent = await cart_payment_repository.get_payment_intent_by_id_from_primary(
            id=payment_intent.id
        )
        assert retrieved_correct_payment_intent
        assert retrieved_correct_payment_intent == payment_intent
        retrieved_incorrect_payment_intent = await cart_payment_repository.get_payment_intent_by_id_from_primary(
            id=uuid4()
        )
        assert not retrieved_incorrect_payment_intent

    @pytest.mark.asyncio
    async def test_update_payment_intent_capture_state(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        captured_at = datetime.now(timezone.utc)
        result = await cart_payment_repository.update_payment_intent_capture_state(
            id=payment_intent.id, status=IntentStatus.SUCCEEDED, captured_at=captured_at
        )

        expected_result = PaymentIntent(
            id=payment_intent.id,
            cart_payment_id=payment_intent.cart_payment_id,
            idempotency_key=payment_intent.idempotency_key,
            amount_initiated=payment_intent.amount_initiated,
            amount=payment_intent.amount,
            application_fee_amount=payment_intent.application_fee_amount,
            capture_method=payment_intent.capture_method,
            country=payment_intent.country,
            currency=payment_intent.currency,
            status=IntentStatus.SUCCEEDED,
            statement_descriptor=payment_intent.statement_descriptor,
            payment_method_id=payment_intent.payment_method_id,
            metadata=payment_intent.metadata,
            legacy_consumer_charge_id=payment_intent.legacy_consumer_charge_id,
            created_at=payment_intent.created_at,
            updated_at=result.updated_at,  # Generated
            captured_at=captured_at,  # Updated
            cancelled_at=payment_intent.cancelled_at,
            capture_after=payment_intent.capture_after,
        )
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_update_payment_intent_amount(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        result = await cart_payment_repository.update_payment_intent_amount(
            id=payment_intent.id, amount=(payment_intent.amount + 100)
        )

        expected_result = PaymentIntent(
            id=payment_intent.id,
            cart_payment_id=payment_intent.cart_payment_id,
            idempotency_key=payment_intent.idempotency_key,
            amount_initiated=payment_intent.amount_initiated,
            amount=(payment_intent.amount + 100),  # Updated
            application_fee_amount=payment_intent.application_fee_amount,
            capture_method=payment_intent.capture_method,
            country=payment_intent.country,
            currency=payment_intent.currency,
            status=payment_intent.status,
            statement_descriptor=payment_intent.statement_descriptor,
            payment_method_id=payment_intent.payment_method_id,
            metadata=payment_intent.metadata,
            legacy_consumer_charge_id=payment_intent.legacy_consumer_charge_id,
            created_at=payment_intent.created_at,
            updated_at=result.updated_at,  # Don't know generated date ahead of time
            captured_at=payment_intent.captured_at,
            cancelled_at=payment_intent.cancelled_at,
            capture_after=payment_intent.capture_after,
        )
        assert result == expected_result


class TestPaymentIntentAdjustmentHistory:
    @pytest.mark.asyncio
    async def test_insert_history(
        self,
        cart_payment_repository: CartPaymentRepository,
        cart_payment: CartPayment,
        payment_method: PgpPaymentMethodDbEntity,
    ):
        payment_intent = await cart_payment_repository.insert_payment_intent(
            id=uuid4(),
            cart_payment_id=cart_payment.id,
            idempotency_key=f"ik_{uuid4()}",
            amount_initiated=100,
            amount=200,
            application_fee_amount=100,
            country=CountryCode.US,
            currency="USD",
            capture_method=CaptureMethod.MANUAL,
            status=IntentStatus.REQUIRES_CAPTURE,
            statement_descriptor=None,
            capture_after=None,
            payment_method_id=payment_method.id,
            metadata=None,
            legacy_consumer_charge_id=LegacyConsumerChargeId(98722),
        )

        id = uuid4()
        result = await cart_payment_repository.insert_payment_intent_adjustment_history(
            id=id,
            payer_id=cart_payment.payer_id,
            payment_intent_id=payment_intent.id,
            amount=payment_intent.amount + 100,
            amount_original=payment_intent.amount,
            amount_delta=100,
            currency=payment_intent.currency,
            idempotency_key=payment_intent.idempotency_key,
        )

        expected_adjustment = PaymentIntentAdjustmentHistory(
            id=id,
            payer_id=cart_payment.payer_id,
            payment_intent_id=payment_intent.id,
            amount=payment_intent.amount + 100,
            amount_original=payment_intent.amount,
            amount_delta=100,
            currency=payment_intent.currency,
            idempotency_key=payment_intent.idempotency_key,
            created_at=result.created_at,  # Do not know exact created_at ahead of time
        )

        assert result == expected_adjustment

    @pytest.mark.asyncio
    async def test_get_payment_intent_adjustment_history(
        self,
        cart_payment_repository: CartPaymentRepository,
        cart_payment: CartPayment,
        payment_intent: PaymentIntent,
    ):
        history_record = await cart_payment_repository.insert_payment_intent_adjustment_history(
            id=uuid4(),
            payer_id=cart_payment.payer_id,
            payment_intent_id=payment_intent.id,
            amount=payment_intent.amount + 100,
            amount_original=payment_intent.amount,
            amount_delta=100,
            currency=payment_intent.currency,
            idempotency_key=str(uuid4()),
        )

        result = await cart_payment_repository.get_payment_intent_adjustment_history_from_primary(
            idempotency_key=history_record.idempotency_key
        )
        assert result == history_record

        result = await cart_payment_repository.get_payment_intent_adjustment_history_from_primary(
            idempotency_key=f"{history_record.idempotency_key}-does-not-exist"
        )
        assert result is None


class TestPgpPaymentIntent:
    @pytest.mark.asyncio
    async def test_update_pgp_payment_intent_status(
        self,
        cart_payment_repository: CartPaymentRepository,
        pgp_payment_intent: PgpPaymentIntent,
    ):
        result = await cart_payment_repository.update_pgp_payment_intent_status(
            id=pgp_payment_intent.id, status=IntentStatus.SUCCEEDED
        )
        assert result

        expected_intent = PgpPaymentIntent(
            id=pgp_payment_intent.id,
            payment_intent_id=pgp_payment_intent.payment_intent_id,
            idempotency_key=pgp_payment_intent.idempotency_key,
            pgp_code=pgp_payment_intent.pgp_code,
            resource_id=pgp_payment_intent.resource_id,
            status=IntentStatus.SUCCEEDED,  # Updated
            invoice_resource_id=pgp_payment_intent.invoice_resource_id,
            charge_resource_id=pgp_payment_intent.charge_resource_id,
            payment_method_resource_id=pgp_payment_intent.payment_method_resource_id,
            customer_resource_id=pgp_payment_intent.customer_resource_id,
            currency=pgp_payment_intent.currency,
            amount=pgp_payment_intent.amount,
            amount_capturable=pgp_payment_intent.amount_capturable,
            amount_received=pgp_payment_intent.amount_received,
            application_fee_amount=pgp_payment_intent.application_fee_amount,
            payout_account_id=pgp_payment_intent.payout_account_id,
            capture_method=pgp_payment_intent.capture_method,
            created_at=pgp_payment_intent.created_at,
            updated_at=result.updated_at,  # Don't know exact date ahead of time
            captured_at=pgp_payment_intent.captured_at,
            cancelled_at=pgp_payment_intent.cancelled_at,
        )
        assert result == expected_intent

    @pytest.mark.asyncio
    async def test_update_pgp_payment_intent_amount(
        self,
        cart_payment_repository: CartPaymentRepository,
        pgp_payment_intent: PgpPaymentIntent,
    ):
        result = await cart_payment_repository.update_pgp_payment_intent_amount(
            id=pgp_payment_intent.id, amount=(pgp_payment_intent.amount + 100)
        )
        assert result

        expected_intent = PgpPaymentIntent(
            id=pgp_payment_intent.id,
            payment_intent_id=pgp_payment_intent.payment_intent_id,
            idempotency_key=pgp_payment_intent.idempotency_key,
            pgp_code=pgp_payment_intent.pgp_code,
            resource_id=pgp_payment_intent.resource_id,
            status=pgp_payment_intent.status,
            invoice_resource_id=pgp_payment_intent.invoice_resource_id,
            charge_resource_id=pgp_payment_intent.charge_resource_id,
            payment_method_resource_id=pgp_payment_intent.payment_method_resource_id,
            customer_resource_id=pgp_payment_intent.customer_resource_id,
            currency=pgp_payment_intent.currency,
            amount=(pgp_payment_intent.amount + 100),  # Updated
            amount_capturable=pgp_payment_intent.amount_capturable,
            amount_received=pgp_payment_intent.amount_received,
            application_fee_amount=pgp_payment_intent.application_fee_amount,
            payout_account_id=pgp_payment_intent.payout_account_id,
            capture_method=pgp_payment_intent.capture_method,
            created_at=pgp_payment_intent.created_at,
            updated_at=result.updated_at,  # Don't know exact date ahead of time
            captured_at=pgp_payment_intent.captured_at,
            cancelled_at=pgp_payment_intent.cancelled_at,
        )
        assert result == expected_intent

    @pytest.mark.asyncio
    async def test_update_pgp_payment_intent(
        self,
        cart_payment_repository: CartPaymentRepository,
        pgp_payment_intent: PgpPaymentIntent,
    ):
        charge_resource_id = f"{pgp_payment_intent.charge_resource_id}-updated"
        resource_id = f"{pgp_payment_intent.resource_id}-updated"
        update_pgp_payment_intent_where_request = UpdatePgpPaymentIntentWhereInput(
            id=pgp_payment_intent.id
        )
        update_pgp_payment_intent_set_request = UpdatePgpPaymentIntentSetInput(
            status=IntentStatus.FAILED,
            charge_resource_id=charge_resource_id,
            resource_id=resource_id,
            amount_capturable=0,
            amount_received=500,
            updated_at=datetime.now(timezone.utc),
        )
        updated_pgp_payment_intent = await cart_payment_repository.update_pgp_payment_intent(
            update_pgp_payment_intent_where_input=update_pgp_payment_intent_where_request,
            update_pgp_payment_intent_set_input=update_pgp_payment_intent_set_request,
        )
        assert updated_pgp_payment_intent
        assert (
            updated_pgp_payment_intent.updated_at
            == update_pgp_payment_intent_set_request.updated_at
        )

        expected_intent = PgpPaymentIntent(
            id=pgp_payment_intent.id,
            payment_intent_id=pgp_payment_intent.payment_intent_id,
            idempotency_key=pgp_payment_intent.idempotency_key,
            pgp_code=pgp_payment_intent.pgp_code,
            resource_id=resource_id,  # Updated
            status=IntentStatus.FAILED,  # Updated
            invoice_resource_id=pgp_payment_intent.invoice_resource_id,
            charge_resource_id=charge_resource_id,  # Updated
            payment_method_resource_id=pgp_payment_intent.payment_method_resource_id,
            customer_resource_id=pgp_payment_intent.customer_resource_id,
            currency=pgp_payment_intent.currency,
            amount=pgp_payment_intent.amount,
            amount_capturable=0,  # Updated
            amount_received=500,  # Updated
            application_fee_amount=pgp_payment_intent.application_fee_amount,
            payout_account_id=pgp_payment_intent.payout_account_id,
            capture_method=pgp_payment_intent.capture_method,
            created_at=pgp_payment_intent.created_at,
            updated_at=updated_pgp_payment_intent.updated_at,  # Generated
            captured_at=pgp_payment_intent.captured_at,
            cancelled_at=pgp_payment_intent.cancelled_at,
        )
        assert updated_pgp_payment_intent == expected_intent

        update_pgp_payment_intent_where_request = UpdatePgpPaymentIntentWhereInput(
            id=pgp_payment_intent.id
        )
        update_pgp_payment_intent_set_request = UpdatePgpPaymentIntentSetInput(
            status=IntentStatus.FAILED,
            charge_resource_id=charge_resource_id,
            resource_id=resource_id,
            amount_capturable=0,
            amount_received=500,
            cancelled_at=datetime.now(timezone.utc),
        )
        cancelled_payment_intent = await cart_payment_repository.update_pgp_payment_intent(
            update_pgp_payment_intent_where_input=update_pgp_payment_intent_where_request,
            update_pgp_payment_intent_set_input=update_pgp_payment_intent_set_request,
        )
        assert cancelled_payment_intent
        assert (
            cancelled_payment_intent.updated_at == updated_pgp_payment_intent.updated_at
        )

    @pytest.mark.asyncio
    async def test_cancel_pgp_payment_intent(
        self,
        cart_payment_repository: CartPaymentRepository,
        pgp_payment_intent: PgpPaymentIntent,
    ):
        charge_resource_id = f"{pgp_payment_intent.charge_resource_id}-updated"
        resource_id = f"{pgp_payment_intent.resource_id}-updated"
        updated_and_cancel_time = datetime.now(timezone.utc)
        cancel_payment_intent_where_request = UpdatePgpPaymentIntentWhereInput(
            id=pgp_payment_intent.id
        )
        cancel_payment_intent_set_request = UpdatePgpPaymentIntentSetInput(
            status=IntentStatus.CANCELLED,
            charge_resource_id=charge_resource_id,
            resource_id=resource_id,
            amount_capturable=0,
            amount_received=500,
            updated_at=updated_and_cancel_time,
            cancelled_at=updated_and_cancel_time,
        )
        result = await cart_payment_repository.update_pgp_payment_intent(
            update_pgp_payment_intent_where_input=cancel_payment_intent_where_request,
            update_pgp_payment_intent_set_input=cancel_payment_intent_set_request,
        )
        assert result
        assert result.updated_at == updated_and_cancel_time
        assert result.cancelled_at == updated_and_cancel_time
        expected_intent = PgpPaymentIntent(
            id=pgp_payment_intent.id,
            payment_intent_id=pgp_payment_intent.payment_intent_id,
            idempotency_key=pgp_payment_intent.idempotency_key,
            pgp_code=pgp_payment_intent.pgp_code,
            resource_id=resource_id,  # Updated
            status=IntentStatus.CANCELLED,  # Updated
            invoice_resource_id=pgp_payment_intent.invoice_resource_id,
            charge_resource_id=charge_resource_id,  # Updated
            payment_method_resource_id=pgp_payment_intent.payment_method_resource_id,
            customer_resource_id=pgp_payment_intent.customer_resource_id,
            currency=pgp_payment_intent.currency,
            amount=pgp_payment_intent.amount,
            amount_capturable=0,  # Updated
            amount_received=500,  # Updated
            application_fee_amount=pgp_payment_intent.application_fee_amount,
            payout_account_id=pgp_payment_intent.payout_account_id,
            capture_method=pgp_payment_intent.capture_method,
            created_at=pgp_payment_intent.created_at,
            updated_at=result.updated_at,  # Updated
            captured_at=pgp_payment_intent.captured_at,
            cancelled_at=result.cancelled_at,  # Updated
        )
        assert result.status == IntentStatus.CANCELLED
        assert result == expected_intent


class TestPaymentCharge:
    @pytest.mark.asyncio
    async def test_insert_payment_charge(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        id = uuid4()
        idempotency_key = str(uuid4())
        result = await cart_payment_repository.insert_payment_charge(
            id=id,
            payment_intent_id=payment_intent.id,
            pgp_code=PgpCode.STRIPE,
            idempotency_key=idempotency_key,
            status=ChargeStatus.REQUIRES_CAPTURE,
            currency="USD",
            amount=400,
            amount_refunded=0,
            application_fee_amount=None,
            payout_account_id=None,
        )

        expected_charge = PaymentCharge(
            id=id,
            payment_intent_id=payment_intent.id,
            pgp_code=PgpCode.STRIPE,
            idempotency_key=idempotency_key,
            status=ChargeStatus.REQUIRES_CAPTURE,
            currency="USD",
            amount=400,
            amount_refunded=0,
            application_fee_amount=None,
            payout_account_id=None,
            created_at=result.created_at,  # Generated dates not known ahead of time
            updated_at=result.updated_at,
            captured_at=None,
            cancelled_at=None,
        )

        assert result == expected_charge

    @pytest.mark.asyncio
    async def test_update_payment_charge_status(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_charge: PaymentCharge,
    ):
        result = await cart_payment_repository.update_payment_charge_status(
            payment_intent_id=payment_charge.payment_intent_id,
            status=ChargeStatus.FAILED,
        )

        expected_charge = PaymentCharge(
            id=payment_charge.id,
            payment_intent_id=payment_charge.payment_intent_id,
            pgp_code=payment_charge.pgp_code,
            idempotency_key=payment_charge.idempotency_key,
            status=ChargeStatus.FAILED,  # Updated
            currency=payment_charge.currency,
            amount=payment_charge.amount,
            amount_refunded=payment_charge.amount_refunded,
            application_fee_amount=payment_charge.application_fee_amount,
            payout_account_id=payment_charge.payout_account_id,
            created_at=payment_charge.created_at,
            updated_at=result.updated_at,  # Generated date not known ahead of time
            captured_at=payment_charge.captured_at,
            cancelled_at=payment_charge.cancelled_at,
        )

        assert result == expected_charge

    @pytest.mark.asyncio
    async def test_update_payment_charge_amount(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_charge: PaymentCharge,
    ):
        result = await cart_payment_repository.update_payment_charge_amount(
            payment_intent_id=payment_charge.payment_intent_id,
            amount=(payment_charge.amount + 100),
        )

        expected_charge = PaymentCharge(
            id=payment_charge.id,
            payment_intent_id=payment_charge.payment_intent_id,
            pgp_code=payment_charge.pgp_code,
            idempotency_key=payment_charge.idempotency_key,
            status=payment_charge.status,
            currency=payment_charge.currency,
            amount=(payment_charge.amount + 100),  # Updated
            amount_refunded=payment_charge.amount_refunded,
            application_fee_amount=payment_charge.application_fee_amount,
            payout_account_id=payment_charge.payout_account_id,
            created_at=payment_charge.created_at,
            updated_at=result.updated_at,  # Generated date not known ahead of time
            captured_at=payment_charge.captured_at,
            cancelled_at=payment_charge.cancelled_at,
        )

        assert result == expected_charge

    @pytest.mark.asyncio
    async def test_update_payment_charge(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_charge: PaymentCharge,
    ):
        result = await cart_payment_repository.update_payment_charge(
            payment_intent_id=payment_charge.payment_intent_id,
            status=ChargeStatus.FAILED,
            amount_refunded=400,
        )

        expected_charge = PaymentCharge(
            id=payment_charge.id,
            payment_intent_id=payment_charge.payment_intent_id,
            pgp_code=payment_charge.pgp_code,
            idempotency_key=payment_charge.idempotency_key,
            status=ChargeStatus.FAILED,  # Updated
            currency=payment_charge.currency,
            amount=payment_charge.amount,
            amount_refunded=400,  # Updated
            application_fee_amount=payment_charge.application_fee_amount,
            payout_account_id=payment_charge.payout_account_id,
            created_at=payment_charge.created_at,
            updated_at=result.updated_at,  # Generated date not known ahead of time
            captured_at=payment_charge.captured_at,
            cancelled_at=payment_charge.cancelled_at,
        )

        assert result == expected_charge


class TestPgpPaymentCharge:
    @pytest.mark.asyncio
    async def test_insert_pgp_payment_charge(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_charge: PaymentCharge,
    ):
        id = uuid4()
        idempotency_key = str(uuid4())
        intent_resource_id = str(uuid4())
        result = await cart_payment_repository.insert_pgp_payment_charge(
            id=id,
            payment_charge_id=payment_charge.id,
            pgp_code=PgpCode.STRIPE,
            idempotency_key=idempotency_key,
            status=ChargeStatus.REQUIRES_CAPTURE,
            currency="USD",
            amount=400,
            amount_refunded=0,
            application_fee_amount=None,
            payout_account_id=None,
            resource_id=None,
            intent_resource_id=intent_resource_id,
            invoice_resource_id=None,
            payment_method_resource_id=intent_resource_id,
        )

        expected_charge = PgpPaymentCharge(
            id=id,
            payment_charge_id=payment_charge.id,
            pgp_code=PgpCode.STRIPE,
            idempotency_key=idempotency_key,
            status=ChargeStatus.REQUIRES_CAPTURE,
            currency="USD",
            amount=400,
            amount_refunded=0,
            application_fee_amount=None,
            payout_account_id=None,
            resource_id=None,
            intent_resource_id=intent_resource_id,
            invoice_resource_id=None,
            payment_method_resource_id=intent_resource_id,
            created_at=result.created_at,
            updated_at=result.updated_at,
            captured_at=None,
            cancelled_at=None,
        )

        assert result == expected_charge

    @pytest.mark.asyncio
    async def test_update_pgp_payment_charge_status(
        self,
        cart_payment_repository: CartPaymentRepository,
        pgp_payment_charge: PgpPaymentCharge,
    ):
        result = await cart_payment_repository.update_pgp_payment_charge_status(
            payment_charge_id=pgp_payment_charge.payment_charge_id,
            status=ChargeStatus.FAILED,
        )

        expected_charge = PgpPaymentCharge(
            id=pgp_payment_charge.id,
            payment_charge_id=pgp_payment_charge.payment_charge_id,
            pgp_code=pgp_payment_charge.pgp_code,
            idempotency_key=pgp_payment_charge.idempotency_key,
            status=ChargeStatus.FAILED,  # Updated
            currency=pgp_payment_charge.currency,
            amount=pgp_payment_charge.amount,
            amount_refunded=pgp_payment_charge.amount_refunded,
            application_fee_amount=pgp_payment_charge.application_fee_amount,
            payout_account_id=pgp_payment_charge.payout_account_id,
            resource_id=pgp_payment_charge.resource_id,
            intent_resource_id=pgp_payment_charge.intent_resource_id,
            invoice_resource_id=pgp_payment_charge.invoice_resource_id,
            payment_method_resource_id=pgp_payment_charge.payment_method_resource_id,
            created_at=pgp_payment_charge.created_at,
            updated_at=result.updated_at,  # Generated date not known ahead of time
            captured_at=pgp_payment_charge.captured_at,
            cancelled_at=pgp_payment_charge.cancelled_at,
        )

        assert result == expected_charge

    @pytest.mark.asyncio
    async def test_update_pgp_payment_charge_amount(
        self,
        cart_payment_repository: CartPaymentRepository,
        pgp_payment_charge: PgpPaymentCharge,
    ):
        result = await cart_payment_repository.update_pgp_payment_charge_amount(
            payment_charge_id=pgp_payment_charge.payment_charge_id,
            amount=(pgp_payment_charge.amount + 100),
        )

        expected_charge = PgpPaymentCharge(
            id=pgp_payment_charge.id,
            payment_charge_id=pgp_payment_charge.payment_charge_id,
            pgp_code=pgp_payment_charge.pgp_code,
            idempotency_key=pgp_payment_charge.idempotency_key,
            status=pgp_payment_charge.status,
            currency=pgp_payment_charge.currency,
            amount=(pgp_payment_charge.amount + 100),  # Updated
            amount_refunded=pgp_payment_charge.amount_refunded,
            application_fee_amount=pgp_payment_charge.application_fee_amount,
            payout_account_id=pgp_payment_charge.payout_account_id,
            resource_id=pgp_payment_charge.resource_id,
            intent_resource_id=pgp_payment_charge.intent_resource_id,
            invoice_resource_id=pgp_payment_charge.invoice_resource_id,
            payment_method_resource_id=pgp_payment_charge.payment_method_resource_id,
            created_at=pgp_payment_charge.created_at,
            updated_at=result.updated_at,  # Generated date not known ahead of time
            captured_at=pgp_payment_charge.captured_at,
            cancelled_at=pgp_payment_charge.cancelled_at,
        )

        assert result == expected_charge

    @pytest.mark.asyncio
    async def test_update_pgp_payment_charge(
        self,
        cart_payment_repository: CartPaymentRepository,
        pgp_payment_charge: PgpPaymentCharge,
    ):
        result = await cart_payment_repository.update_pgp_payment_charge(
            payment_charge_id=pgp_payment_charge.payment_charge_id,
            status=ChargeStatus.SUCCEEDED,
            amount=300,
            amount_refunded=300,
        )

        expected_charge = PgpPaymentCharge(
            id=pgp_payment_charge.id,
            payment_charge_id=pgp_payment_charge.payment_charge_id,
            pgp_code=pgp_payment_charge.pgp_code,
            idempotency_key=pgp_payment_charge.idempotency_key,
            status=ChargeStatus.SUCCEEDED,  # Updated
            currency=pgp_payment_charge.currency,
            amount=300,  # Updated
            amount_refunded=300,  # Updated
            application_fee_amount=pgp_payment_charge.application_fee_amount,
            payout_account_id=pgp_payment_charge.payout_account_id,
            resource_id=pgp_payment_charge.resource_id,
            intent_resource_id=pgp_payment_charge.intent_resource_id,
            invoice_resource_id=pgp_payment_charge.invoice_resource_id,
            payment_method_resource_id=pgp_payment_charge.payment_method_resource_id,
            created_at=pgp_payment_charge.created_at,
            updated_at=result.updated_at,  # Generated date not known ahead of time
            captured_at=pgp_payment_charge.captured_at,
            cancelled_at=pgp_payment_charge.cancelled_at,
        )

        assert result == expected_charge


class TestUpdatePaymentIntentStatus:
    @pytest.mark.asyncio
    async def test_success_returns_row(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        update_payment_intent_status_where_input = UpdatePaymentIntentWhereInput(
            id=payment_intent.id, previous_status=IntentStatus.REQUIRES_CAPTURE.value
        )
        update_payment_intent_status_set_input = UpdatePaymentIntentSetInput(
            status=IntentStatus.CAPTURING.value, updated_at=datetime.now(timezone.utc)
        )
        payment_intent = await cart_payment_repository.update_payment_intent(
            update_payment_intent_status_where_input=update_payment_intent_status_where_input,
            update_payment_intent_status_set_input=update_payment_intent_status_set_input,
        )
        assert payment_intent.status == IntentStatus.CAPTURING.value
        assert (
            payment_intent.updated_at
            == update_payment_intent_status_set_input.updated_at
        )

    @pytest.mark.asyncio
    async def test_update_payment_intent_success_returns_row(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        update_payment_intent_status_where_input = UpdatePaymentIntentWhereInput(
            id=payment_intent.id, previous_status=IntentStatus.REQUIRES_CAPTURE.value
        )
        now = datetime.now(timezone.utc)
        update_payment_intent_status_set_input = UpdatePaymentIntentSetInput(
            status=IntentStatus.CAPTURING.value, updated_at=now
        )
        updated_payment_intent = await cart_payment_repository.update_payment_intent(
            update_payment_intent_status_where_input=update_payment_intent_status_where_input,
            update_payment_intent_status_set_input=update_payment_intent_status_set_input,
        )
        assert updated_payment_intent.status == IntentStatus.CAPTURING.value
        assert (
            updated_payment_intent.updated_at
            == update_payment_intent_status_set_input.updated_at
        )
        assert (
            updated_payment_intent.capture_after == payment_intent.capture_after
        ), "capture_after shouldn't change when not specified in update input"
        assert (
            updated_payment_intent.cancelled_at is None
        )  # cancelled_at is not updated
        assert updated_payment_intent.amount == payment_intent.amount  # No change
        assert (
            updated_payment_intent.application_fee_amount
            == payment_intent.application_fee_amount
        )  # No change

        update_payment_intent_status_where_input = UpdatePaymentIntentWhereInput(
            id=payment_intent.id, previous_status=IntentStatus.CAPTURING.value
        )
        now = datetime.now(timezone.utc)
        new_capture_after = datetime.utcnow() + timedelta(days=100)
        update_payment_intent_status_set_input = UpdatePaymentIntentSetInput(
            status=IntentStatus.CAPTURING.value,
            updated_at=now,
            capture_after=new_capture_after,
        )
        updated_payment_intent = await cart_payment_repository.update_payment_intent(
            update_payment_intent_status_where_input=update_payment_intent_status_where_input,
            update_payment_intent_status_set_input=update_payment_intent_status_set_input,
        )
        assert updated_payment_intent.capture_after == new_capture_after

        now = datetime.now(timezone.utc)
        cancel_payment_intent_status_where_input = UpdatePaymentIntentWhereInput(
            id=payment_intent.id, previous_status=IntentStatus.CAPTURING.value
        )
        cancel_payment_intent_status_set_input = UpdatePaymentIntentSetInput(
            status=IntentStatus.CANCELLED.value, cancelled_at=now
        )
        cancelled_payment_intent = await cart_payment_repository.update_payment_intent(
            update_payment_intent_status_where_input=cancel_payment_intent_status_where_input,
            update_payment_intent_status_set_input=cancel_payment_intent_status_set_input,
        )
        assert cancelled_payment_intent
        assert (
            cancelled_payment_intent.cancelled_at
            == cancel_payment_intent_status_set_input.cancelled_at
        )
        assert (
            cancelled_payment_intent.updated_at == updated_payment_intent.updated_at
        )  # updated_at is un-changed

    @pytest.mark.asyncio
    async def test_cancel_payment_intent_success_returns_row(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        update_payment_intent_status_where_input = UpdatePaymentIntentWhereInput(
            id=payment_intent.id, previous_status=IntentStatus.REQUIRES_CAPTURE.value
        )
        now = datetime.now(timezone.utc)
        update_payment_intent_status_set_input = UpdatePaymentIntentSetInput(
            status=IntentStatus.CANCELLED.value, updated_at=now, cancelled_at=now
        )
        cancelled_payment_intent = await cart_payment_repository.update_payment_intent(
            update_payment_intent_status_where_input=update_payment_intent_status_where_input,
            update_payment_intent_status_set_input=update_payment_intent_status_set_input,
        )
        assert cancelled_payment_intent.status == IntentStatus.CANCELLED.value
        assert (
            cancelled_payment_intent.updated_at
            == update_payment_intent_status_set_input.updated_at
        )
        assert (
            cancelled_payment_intent.cancelled_at
            == update_payment_intent_status_set_input.cancelled_at
        )
        assert cancelled_payment_intent.amount == payment_intent.amount  # No change
        assert (
            cancelled_payment_intent.application_fee_amount
            == payment_intent.application_fee_amount
        )  # No change

    @pytest.mark.asyncio
    async def test_failure_returns_nothing(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        with pytest.raises(PaymentIntentCouldNotBeUpdatedError):
            await cart_payment_repository.update_payment_intent(
                update_payment_intent_status_where_input=UpdatePaymentIntentWhereInput(
                    id=payment_intent.id, previous_status=IntentStatus.INIT.value
                ),
                update_payment_intent_status_set_input=UpdatePaymentIntentSetInput(
                    status=IntentStatus.CAPTURING.value,
                    updated_at=datetime.now(timezone.utc),
                ),
            )


class TestCartPayment:
    @pytest.mark.asyncio
    async def test_get_cart_payment_by_id(
        self, cart_payment_repository: CartPaymentRepository, cart_payment: CartPayment
    ):
        # No result
        result = await cart_payment_repository.get_cart_payment_by_id_from_primary(
            cart_payment_id=uuid4()
        )
        assert result == (None, None)

        # Match
        result = await cart_payment_repository.get_cart_payment_by_id_from_primary(
            cart_payment_id=cart_payment.id
        )

        expected_legacy_payment = LegacyPayment(
            dd_consumer_id=1,
            dd_country_id=None,
            dd_stripe_card_id=1,
            stripe_charge_id=None,
            stripe_customer_id=PgpPayerResourceId("stripe_customer_id"),
            stripe_card_id=PgpPaymentMethodResourceId("stripe_card_id"),
        )
        assert result == (cart_payment, expected_legacy_payment)

    @pytest.mark.asyncio
    async def test_get_cart_payment_by_reference_id(
        self, cart_payment_repository: CartPaymentRepository, cart_payment: CartPayment
    ):
        result = await cart_payment_repository.get_most_recent_cart_payment_by_reference_id_from_primary(
            input=GetCartPaymentsByReferenceId(
                reference_id=cart_payment.correlation_ids.reference_id,
                reference_type=cart_payment.correlation_ids.reference_type,
            )
        )
        assert result
        assert result == cart_payment

    @pytest.mark.asyncio
    async def test_insert_cart_payment(
        self, cart_payment_repository: CartPaymentRepository, payer: PayerDbEntity
    ):
        id = uuid4()
        result = await cart_payment_repository.insert_cart_payment(
            id=id,
            payer_id=UUID(str(payer.id)),
            amount_original=99,
            amount_total=100,
            client_description="Test description",
            reference_id="99",
            reference_type="88",
            delay_capture=True,
            metadata=None,
            legacy_consumer_id=1,
            legacy_stripe_card_id=1,
            legacy_provider_customer_id="stripe_customer_id",
            legacy_provider_card_id="stripe_card_id",
        )

        expected_cart_payment = CartPayment(
            id=id,
            amount=100,
            payer_id=payer.id,
            payment_method_id=None,  # Derived field
            delay_capture=True,
            correlation_ids=CorrelationIds(reference_id="99", reference_type="88"),
            metadata=None,
            created_at=result.created_at,  # Generated field
            updated_at=result.updated_at,  # Generated field
            client_description="Test description",
            payer_statement_description=None,  # Generated field
            split_payment=None,  # Derived field
            capture_after=None,
            deleted_at=None,
        )

        assert result == expected_cart_payment

    @pytest.mark.asyncio
    async def test_update_cart_payment_details(
        self, cart_payment_repository: CartPaymentRepository, payer: PayerDbEntity
    ):
        cart_payment = await cart_payment_repository.insert_cart_payment(
            id=uuid4(),
            payer_id=UUID(str(payer.id)),
            amount_original=99,
            amount_total=100,
            client_description="Test description",
            reference_id="99",
            reference_type="88",
            delay_capture=True,
            metadata=None,
            legacy_consumer_id=1,
            legacy_stripe_card_id=1,
            legacy_provider_customer_id="stripe_customer_id",
            legacy_provider_card_id="stripe_card_id",
        )

        new_amount = cart_payment.amount + 100
        new_description = f"{cart_payment.client_description}-updated"
        result = await cart_payment_repository.update_cart_payment_details(
            cart_payment_id=cart_payment.id,
            amount=new_amount,
            client_description=new_description,
        )

        expected_cart_payment = cart_payment
        expected_cart_payment.amount = new_amount
        expected_cart_payment.client_description = new_description
        expected_cart_payment.updated_at = result.updated_at  # Generated
        assert result == expected_cart_payment

    @pytest.mark.asyncio
    async def test_update_cart_payments_remove_pii(
        self, cart_payment_repository: CartPaymentRepository
    ):
        await cart_payment_repository.insert_cart_payment(
            id=uuid4(),
            payer_id=None,
            amount_original=99,
            amount_total=100,
            client_description=None,
            reference_id="99",
            reference_type="88",
            delay_capture=False,
            metadata=None,
            legacy_consumer_id=120,
            legacy_stripe_card_id=1,
            legacy_provider_customer_id="stripe_customer_id",
            legacy_provider_card_id="stripe_card_id",
        )
        updated_cart_payments = await cart_payment_repository.update_cart_payments_remove_pii(
            update_cart_payments_remove_pii_where_input=UpdateCartPaymentsRemovePiiWhereInput(
                legacy_consumer_id=120
            ),
            update_cart_payments_remove_pii_set_input=UpdateCartPaymentsRemovePiiSetInput(
                client_description=DeletePayerRedactingText.REDACTED
            ),
        )
        assert len(updated_cart_payments) == 1
        assert (
            updated_cart_payments[0].client_description
            == DeletePayerRedactingText.REDACTED
        )

        await cart_payment_repository.payment_database.master().execute(
            cart_payments.table.delete().where(cart_payments.legacy_consumer_id == 120)
        )

    @pytest.mark.asyncio
    async def test_cancel_cart_payment(
        self, cart_payment_repository: CartPaymentRepository, payer: PayerDbEntity
    ):
        cart_payment = await cart_payment_repository.insert_cart_payment(
            id=uuid4(),
            payer_id=UUID(str(payer.id)),
            amount_original=99,
            amount_total=100,
            client_description="Test description",
            reference_id="99",
            reference_type="88",
            delay_capture=True,
            metadata=None,
            legacy_consumer_id=1,
            legacy_stripe_card_id=1,
            legacy_provider_customer_id="stripe_customer_id",
            legacy_provider_card_id="stripe_card_id",
        )
        now = datetime.now(timezone.utc)
        cancelled_cart_payment = await cart_payment_repository.update_cart_payment_post_cancellation(
            update_cart_payment_post_cancellation_input=UpdateCartPaymentPostCancellationInput(
                id=cart_payment.id, updated_at=now, deleted_at=now
            )
        )
        assert cancelled_cart_payment.deleted_at is not None
        assert isinstance(cancelled_cart_payment.deleted_at, datetime)
        assert cancelled_cart_payment.deleted_at == cancelled_cart_payment.updated_at


class TestRefunds:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "refund_reason",
        [None, RefundReason.REQUESTED_BY_CUSTOMER],
        ids=["No reason", f"Reason {RefundReason.REQUESTED_BY_CUSTOMER.value}"],
    )
    async def test_insert_refund(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
        refund_reason: Optional[RefundReason],
    ):
        id = uuid4()
        result = await cart_payment_repository.insert_refund(
            id=id,
            payment_intent_id=payment_intent.id,
            idempotency_key=payment_intent.idempotency_key,
            status=RefundStatus.PROCESSING,
            amount=payment_intent.amount,
            reason=refund_reason,
        )

        expected_refund = Refund(
            id=id,
            payment_intent_id=payment_intent.id,
            idempotency_key=payment_intent.idempotency_key,
            status=RefundStatus.PROCESSING,
            amount=payment_intent.amount,
            reason=refund_reason,
            created_at=result.created_at,  # Generated
            updated_at=result.updated_at,  # Generated
        )

        assert result == expected_refund

    @pytest.mark.asyncio
    async def test_get_refund_by_idempotency_key(
        self, cart_payment_repository: CartPaymentRepository, refund: Refund
    ):
        result = await cart_payment_repository.get_refund_by_idempotency_key_from_primary(
            refund.idempotency_key
        )
        assert result == refund

        result = await cart_payment_repository.get_refund_by_idempotency_key_from_primary(
            f"{refund.idempotency_key}-does-not-exist"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_refund_status(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        idempotency_key = str(uuid4())
        refund = await cart_payment_repository.insert_refund(
            id=uuid4(),
            payment_intent_id=payment_intent.id,
            idempotency_key=idempotency_key,
            status=RefundStatus.PROCESSING,
            amount=500,
            reason=RefundReason.REQUESTED_BY_CUSTOMER,
        )
        result = await cart_payment_repository.update_refund_status(
            refund.id, RefundStatus.FAILED
        )

        expected_refund = Refund(
            id=refund.id,
            payment_intent_id=payment_intent.id,
            idempotency_key=idempotency_key,
            status=RefundStatus.FAILED,
            amount=refund.amount,
            reason=refund.reason,
            created_at=refund.created_at,
            updated_at=result.updated_at,  # Generated
        )

        assert result == expected_refund

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "refund_reason",
        [None, RefundReason.REQUESTED_BY_CUSTOMER],
        ids=["No reason", f"Reason {RefundReason.REQUESTED_BY_CUSTOMER.value}"],
    )
    async def test_insert_pgp_refund(
        self,
        cart_payment_repository: CartPaymentRepository,
        refund: Refund,
        refund_reason: Optional[RefundReason],
    ):
        id = uuid4()
        result = await cart_payment_repository.insert_pgp_refund(
            id=id,
            refund_id=refund.id,
            idempotency_key=refund.idempotency_key,
            status=RefundStatus.PROCESSING,
            pgp_code=PgpCode.STRIPE,
            pgp_resource_id=None,
            pgp_charge_resource_id=None,
            amount=refund.amount,
            reason=refund_reason,
        )

        expected_pgp_refund = PgpRefund(
            id=id,
            refund_id=refund.id,
            idempotency_key=refund.idempotency_key,
            status=RefundStatus.PROCESSING,
            reason=refund_reason,
            pgp_code=PgpCode.STRIPE,
            pgp_resource_id=None,
            charge_resource_id=None,
            amount=refund.amount,
            created_at=result.created_at,  # Generated
            updated_at=result.updated_at,  # Generated
        )

        assert result == expected_pgp_refund

    @pytest.mark.asyncio
    async def test_get_pgp_refund_by_refund_id(
        self, cart_payment_repository: CartPaymentRepository, pgp_refund: PgpRefund
    ):
        result = await cart_payment_repository.get_pgp_refund_by_refund_id_from_primary(
            pgp_refund.refund_id
        )
        assert result == pgp_refund

    @pytest.mark.asyncio
    async def test_updated_pgp_refund(
        self, cart_payment_repository: CartPaymentRepository, refund: Refund
    ):
        pgp_refund = await cart_payment_repository.insert_pgp_refund(
            id=uuid4(),
            refund_id=refund.id,
            idempotency_key=refund.idempotency_key,
            status=RefundStatus.PROCESSING,
            pgp_code=PgpCode.STRIPE,
            amount=refund.amount,
            reason=refund.reason,
            pgp_resource_id=None,
            pgp_charge_resource_id=None,
        )

        result = await cart_payment_repository.update_pgp_refund(
            pgp_refund_id=pgp_refund.id,
            status=RefundStatus.SUCCEEDED,
            pgp_resource_id="test resource id",
            pgp_charge_resource_id="test charge id",
        )

        expected_pgp_refund = PgpRefund(
            id=pgp_refund.id,
            refund_id=refund.id,
            idempotency_key=refund.idempotency_key,
            status=RefundStatus.SUCCEEDED,
            reason=refund.reason,
            pgp_code=PgpCode.STRIPE,
            pgp_resource_id="test resource id",
            pgp_charge_resource_id="test charge id",
            amount=refund.amount,
            created_at=pgp_refund.created_at,
            updated_at=result.updated_at,  # Generated
        )
        assert result == expected_pgp_refund


class TestLegacyCharges:
    @pytest.fixture
    async def consumer_charge(self, cart_payment_repository: CartPaymentRepository):
        now = datetime.now(timezone.utc)
        yield await cart_payment_repository.insert_legacy_consumer_charge(
            target_ct_id=1,
            target_id=2,
            consumer_id=1,  # Use of pre-seeded consumer to satisfy FK constraint
            idempotency_key=str(uuid4()),
            is_stripe_connect_based=False,
            country_id=LegacyCountryId.US,
            currency=Currency.USD,
            stripe_customer_id=None,
            total=800,
            original_total=800,
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    async def stripe_charge(
        self,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        yield await cart_payment_repository.insert_legacy_stripe_charge(
            stripe_id=str(uuid4()),
            card_id=1,
            charge_id=consumer_charge.id,
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.SUCCEEDED,
            idempotency_key=str(uuid4()),
            additional_payment_info="{'test_key': 'test_value'}",
            description="test description",
            error_reason="",
        )

    @pytest.mark.asyncio
    async def test_insert_legacy_consumer_charge(
        self, cart_payment_repository: CartPaymentRepository
    ):
        idempotency_key = str(uuid4())
        now = datetime.now(timezone.utc)
        result = await cart_payment_repository.insert_legacy_consumer_charge(
            target_ct_id=1,
            target_id=2,
            consumer_id=1,  # Use of pre-seeded consumer to satisfy FK constraint
            idempotency_key=idempotency_key,
            is_stripe_connect_based=False,
            country_id=LegacyCountryId.US,
            currency=Currency.USD,
            stripe_customer_id=None,
            total=800,
            original_total=800,
            created_at=now,
            updated_at=now,
        )

        expected_consumer_charge = LegacyConsumerCharge(
            id=LegacyConsumerChargeId(result.id),  # Generated
            target_ct_id=1,
            target_id=2,
            idempotency_key=idempotency_key,
            is_stripe_connect_based=False,
            total=800,
            original_total=800,
            currency=Currency.USD,
            country_id=LegacyCountryId.US,
            issue_id=None,
            stripe_customer_id=None,
            created_at=result.created_at,  # Generated
            updated_at=result.updated_at,  # Generated
        )

        assert result == expected_consumer_charge

    @pytest.mark.asyncio
    async def test_insert_legacy_consumer_charge_with_none_updated_at(
        self, cart_payment_repository: CartPaymentRepository
    ):
        idempotency_key = str(uuid4())
        now = datetime.now(timezone.utc)
        result = await cart_payment_repository.insert_legacy_consumer_charge(
            target_ct_id=1,
            target_id=2,
            consumer_id=1,  # Use of pre-seeded consumer to satisfy FK constraint
            idempotency_key=idempotency_key,
            is_stripe_connect_based=False,
            country_id=LegacyCountryId.US,
            currency=Currency.USD,
            stripe_customer_id=None,
            total=800,
            original_total=800,
            created_at=now,
            updated_at=None,
        )

        expected_consumer_charge = LegacyConsumerCharge(
            id=LegacyConsumerChargeId(result.id),  # Generated
            target_ct_id=1,
            target_id=2,
            idempotency_key=idempotency_key,
            is_stripe_connect_based=False,
            total=800,
            original_total=800,
            currency=Currency.USD,
            country_id=LegacyCountryId.US,
            issue_id=None,
            stripe_customer_id=None,
            created_at=result.created_at,  # Generated
            updated_at=result.updated_at,  # Generated
        )

        assert result == expected_consumer_charge
        assert result.updated_at is None

    @pytest.mark.asyncio
    async def test_get_legacy_consumer_charge_by_id(
        self,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        result = await cart_payment_repository.get_legacy_consumer_charge_by_id(
            consumer_charge.id
        )
        assert result == consumer_charge

    @pytest.mark.asyncio
    async def test_get_legacy_consumer_charge_by_reference_id(
        self,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        result = await cart_payment_repository.get_legacy_consumer_charge_by_reference_id(
            input=GetConsumerChargeByReferenceId(
                target_id=consumer_charge.target_id,
                target_ct_id=consumer_charge.target_ct_id,
            )
        )
        assert result
        assert result.target_id == consumer_charge.target_id
        assert result.target_ct_id == consumer_charge.target_ct_id

    @pytest.mark.asyncio
    async def test_get_legacy_consumer_charge_ids_by_consumer_id(
        self,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        results = await cart_payment_repository.get_legacy_consumer_charge_ids_by_consumer_id(
            get_legacy_consumer_charge_ids_by_consumer_id_input=GetLegacyConsumerChargeIdsByConsumerIdInput(
                consumer_id=1
            )
        )
        assert consumer_charge.id in results

    @pytest.mark.asyncio
    async def test_insert_legacy_stripe_charge(
        self,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        idempotency_key = str(uuid4())
        result = await cart_payment_repository.insert_legacy_stripe_charge(
            stripe_id="stripe_id",
            card_id=None,
            charge_id=consumer_charge.id,
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.SUCCEEDED,
            idempotency_key=idempotency_key,
            additional_payment_info="{'test_key': 'test_value'}",
            description="Test description",
            error_reason="",
        )

        expected_stripe_charge = LegacyStripeCharge(
            id=result.id,  # Generated
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.SUCCEEDED.value,
            error_reason="",
            additional_payment_info="{'test_key': 'test_value'}",
            description="Test description",
            idempotency_key=idempotency_key,
            card_id=None,
            charge_id=consumer_charge.id,
            stripe_id="stripe_id",
            created_at=result.created_at,  # Generated
            updated_at=result.updated_at,  # Generated
            refunded_at=None,
        )

        assert result == expected_stripe_charge

    @pytest.mark.asyncio
    async def test_update_legacy_stripe_charge_add_to_amount_refunded(
        self,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge: LegacyStripeCharge,
    ):
        refunded_at = datetime.now(timezone.utc)
        result = await cart_payment_repository.update_legacy_stripe_charge_add_to_amount_refunded(
            stripe_id=stripe_charge.stripe_id,
            additional_amount_refunded=200,
            refunded_at=refunded_at,
        )

        expected_result = stripe_charge
        expected_result.amount_refunded = 200
        expected_result.refunded_at = refunded_at
        expected_result.updated_at = result.updated_at  # Generated
        assert result == expected_result

        # Call a second time, verify amount_refunded was added to
        refunded_at = datetime.now(timezone.utc)
        result = await cart_payment_repository.update_legacy_stripe_charge_add_to_amount_refunded(
            stripe_id=stripe_charge.stripe_id,
            additional_amount_refunded=300,
            refunded_at=refunded_at,
        )

        expected_result = stripe_charge
        expected_result.amount_refunded = 500
        expected_result.refunded_at = refunded_at
        expected_result.updated_at = result.updated_at  # Generated
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_update_legacy_stripe_charge_refund(
        self,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge: LegacyStripeCharge,
    ):
        refunded_at = datetime.now(timezone.utc)
        result = await cart_payment_repository.update_legacy_stripe_charge_refund(
            stripe_id=stripe_charge.stripe_id,
            amount_refunded=200,
            refunded_at=refunded_at,
        )

        expected_result = stripe_charge
        expected_result.amount_refunded = 200
        expected_result.refunded_at = refunded_at
        expected_result.updated_at = result.updated_at  # Generated
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_update_legacy_stripe_charge_provider_details(
        self,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge: LegacyStripeCharge,
    ):
        result = await cart_payment_repository.update_legacy_stripe_charge_provider_details(
            id=stripe_charge.id,
            stripe_id=f"stripe-{stripe_charge.id}",
            amount=450,
            amount_refunded=300,
            status=LegacyStripeChargeStatus.SUCCEEDED,
        )

        expected_result = stripe_charge
        expected_result.stripe_id = f"stripe-{stripe_charge.id}"
        expected_result.amount = 450
        expected_result.amount_refunded = 300
        expected_result.status = LegacyStripeChargeStatus.SUCCEEDED
        expected_result.updated_at = result.updated_at  # Generated
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_update_legacy_stripe_charge_status(
        self,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge: LegacyStripeCharge,
    ):
        result = await cart_payment_repository.update_legacy_stripe_charge_status(
            stripe_charge_id=stripe_charge.stripe_id,
            status=LegacyStripeChargeStatus.FAILED,
        )

        expected_result = stripe_charge
        expected_result.status = LegacyStripeChargeStatus.FAILED
        expected_result.updated_at = result.updated_at  # Generated
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_update_legacy_stripe_charge_error_details(
        self,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        # Create a stripe charge without stripe_id set, in pending state
        stripe_charge = await cart_payment_repository.insert_legacy_stripe_charge(
            stripe_id="",
            card_id=1,
            charge_id=consumer_charge.id,
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.PENDING,
            idempotency_key=str(uuid4()),
            additional_payment_info="{'test_key': 'test_value'}",
            description="test description",
            error_reason="",
        )

        update_where_input = UpdateLegacyStripeChargeErrorDetailsWhereInput(
            id=stripe_charge.id, previous_status=LegacyStripeChargeStatus.PENDING
        )
        updated_at = datetime.now(timezone.utc)
        update_set_input = UpdateLegacyStripeChargeErrorDetailsSetInput(
            stripe_id="generated id",
            status=LegacyStripeChargeStatus.FAILED,
            error_reason="generic error",
            updated_at=updated_at,
        )

        result = await cart_payment_repository.update_legacy_stripe_charge_error_details(
            update_legacy_stripe_charge_where_input=update_where_input,
            update_legacy_stripe_charge_set_input=update_set_input,
        )
        assert result
        expected_result = stripe_charge
        expected_result.stripe_id = "generated id"
        expected_result.status = LegacyStripeChargeStatus.FAILED
        expected_result.error_reason = "generic error"
        expected_result.updated_at = updated_at
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_update_legacy_stripe_charge_error_details_not_updated(
        self,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        # Create a stripe charge without stripe_id set
        stripe_charge = await cart_payment_repository.insert_legacy_stripe_charge(
            stripe_id=str(uuid4()),
            card_id=1,
            charge_id=consumer_charge.id,
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.SUCCEEDED,
            idempotency_key=str(uuid4()),
            additional_payment_info="{'test_key': 'test_value'}",
            description="test description",
            error_reason="",
        )

        update_where_input = UpdateLegacyStripeChargeErrorDetailsWhereInput(
            id=stripe_charge.id, previous_status=LegacyStripeChargeStatus.PENDING
        )
        update_set_input = UpdateLegacyStripeChargeErrorDetailsSetInput(
            stripe_id="generated id",
            status=LegacyStripeChargeStatus.FAILED,
            error_reason="generic error",
            updated_at=datetime.now(timezone.utc),
        )

        with pytest.raises(LegacyStripeChargeCouldNotBeUpdatedError):
            await cart_payment_repository.update_legacy_stripe_charge_error_details(
                update_legacy_stripe_charge_where_input=update_where_input,
                update_legacy_stripe_charge_set_input=update_set_input,
            )

        # Ensure original record was not modified
        existing_charge = await cart_payment_repository.get_legacy_stripe_charge_by_stripe_id(
            stripe_charge_id=stripe_charge.stripe_id
        )
        assert existing_charge
        expected_existing_charge = stripe_charge
        # Generated fields
        expected_existing_charge.created_at = existing_charge.created_at
        expected_existing_charge.updated_at = existing_charge.updated_at
        assert existing_charge == expected_existing_charge

    @pytest.mark.asyncio
    async def test_get_legacy_stripe_charge_by_stripe_id(
        self,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge: LegacyStripeCharge,
    ):
        result = await cart_payment_repository.get_legacy_stripe_charge_by_stripe_id(
            stripe_charge_id=stripe_charge.stripe_id
        )
        assert result == stripe_charge

    @pytest.mark.asyncio
    async def test_update_stripe_charge_remove_pii(
        self,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge,
        consumer_charge,
    ):
        updated_stripe_charge = await cart_payment_repository.update_legacy_stripe_charge_remove_pii(
            update_legacy_stripe_charge_remove_pii_where_input=UpdateLegacyStripeChargeRemovePiiWhereInput(
                id=stripe_charge.id
            ),
            update_legacy_stripe_charge_remove_pii_set_input=UpdateLegacyStripeChargeRemovePiiSetInput(
                description=DeletePayerRedactingText.REDACTED
            ),
        )

        assert updated_stripe_charge
        assert updated_stripe_charge.description == DeletePayerRedactingText.REDACTED


class TestFindPaymentIntentsThatRequireCapture:
    test_data = [
        # capturable_before_offset_sec, earliest_capture_after_offset_sec
        pytest.param(
            0,
            0,
            True,
            id="[found], intent.capture_after=capturable_before, intent.capture_after=earliest_capture_after",
        ),
        pytest.param(
            0,
            1,
            False,
            id="[excluded], intent.capture_after=capturable_before, intent.capture_after<earliest_capture_after",
        ),
        pytest.param(
            0,
            -1,
            True,
            id="[found], intent.capture_after=capturable_before, intent.capture_after>earliest_capture_after",
        ),
        pytest.param(
            1,
            0,
            True,
            id="[found], intent.capture_after<capturable_before, intent.capture_after=earliest_capture_after",
        ),
        pytest.param(
            1,
            1,
            False,
            id="[excluded], intent.capture_after<capturable_before, intent.capture_after<earliest_capture_after",
        ),
        pytest.param(
            1,
            -1,
            True,
            id="[found], intent.capture_after<capturable_before, intent.capture_after>earliest_capture_after",
        ),
        pytest.param(
            -1,
            0,
            False,
            id="[excluded], intent.capture_after>capturable_before, intent.capture_after=earliest_capture_after",
        ),
        pytest.param(
            -1,
            1,
            False,
            id="[excluded], intent.capture_after>capturable_before, intent.capture_after<earliest_capture_after",
        ),
        pytest.param(
            -1,
            -1,
            False,
            id="[excluded], intent.capture_after>capturable_before, intent.capture_after>earliest_capture_after",
        ),
    ]

    @pytest.mark.parametrize(
        "capturable_before_offset_sec, earliest_capture_after_offset_sec, should_found",
        test_data,
    )
    @pytest.mark.asyncio
    async def test_find_payment_intents_that_require_capture(
        self,
        capturable_before_offset_sec: int,
        earliest_capture_after_offset_sec: int,
        should_found: bool,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        assert payment_intent.capture_after
        results = cart_payment_repository.find_payment_intents_that_require_capture(
            capturable_before=payment_intent.capture_after
            + timedelta(seconds=capturable_before_offset_sec),
            earliest_capture_after=payment_intent.capture_after
            + timedelta(seconds=earliest_capture_after_offset_sec),
        )
        ids = [i.id async for i in results]
        if should_found:
            assert (
                payment_intent.id in ids
            ), f"expected included payment_intent={payment_intent}"
        else:
            assert (
                payment_intent.id not in ids
            ), f"expected excluded payment_intent={payment_intent}"


class TestFindPaymentIntentsInCapturingState:
    @pytest.fixture
    async def payment_intent_in_capturing(
        self,
        cart_payment_repository: CartPaymentRepository,
        payer: PayerDbEntity,
        payment_method: PgpPaymentMethodDbEntity,
        payment_intent__capture_after: datetime,
    ) -> PaymentIntent:
        return await create_payment_intent(
            cart_payment_repository=cart_payment_repository,
            payer=payer,
            payment_method=payment_method,
            payment_intent__capture_after=payment_intent__capture_after,
            intent_status=IntentStatus.CAPTURING,
        )

    test_data = [
        # update_before_offset_sec, earliest_capture_after_offset_sec
        pytest.param(
            0, True, id="[found], intent.capture_after=earliest_capture_after"
        ),
        pytest.param(
            1, False, id="[excluded], intent.capture_after<earliest_capture_after"
        ),
        pytest.param(
            -1, True, id="[found], intent.capture_after>earliest_capture_after"
        ),
    ]

    @pytest.mark.parametrize(
        "earliest_capture_after_offset_sec, should_found", test_data
    )
    @pytest.mark.asyncio
    async def test_find_payment_intents_that_require_capture(
        self,
        earliest_capture_after_offset_sec: int,
        should_found: bool,
        cart_payment_repository: CartPaymentRepository,
        payment_intent_in_capturing: PaymentIntent,
    ):
        assert payment_intent_in_capturing.capture_after
        results = await cart_payment_repository.find_payment_intents_in_capturing(
            earliest_capture_after=payment_intent_in_capturing.capture_after
            + timedelta(seconds=earliest_capture_after_offset_sec)
        )
        ids = [i.id for i in results]
        if should_found:
            assert (
                payment_intent_in_capturing.id in ids
            ), f"expected included payment_intent={payment_intent_in_capturing}"
        else:
            assert (
                payment_intent_in_capturing.id not in ids
            ), f"expected excluded payment_intent={payment_intent_in_capturing}"


class TestCountPaymentIntentsInProblematicStates:
    @pytest.mark.asyncio
    async def test_success(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_method: PgpPaymentMethodDbEntity,
        payment_intent: PaymentIntent,
        payer: PayerDbEntity,
        payment_intent__capture_after: datetime,
    ):
        # Our databases are not data-less for each test run, so we need to count the payment intents before and after
        # to write this test. This is so dirty!
        result_before = await cart_payment_repository.count_payment_intents_in_problematic_states(
            problematic_threshold=timedelta(days=2)
        )

        # Following 3 intents are not problematic
        await create_payment_intent(
            cart_payment_repository,
            payment_method=payment_method,
            payer=payer,
            payment_intent__capture_after=utcnow() - timedelta(days=3),
            intent_status=IntentStatus.FAILED,
        )
        await create_payment_intent(
            cart_payment_repository,
            payment_method=payment_method,
            payer=payer,
            payment_intent__capture_after=utcnow() - timedelta(days=3),
            intent_status=IntentStatus.SUCCEEDED,
        )
        await create_payment_intent(
            cart_payment_repository,
            payment_method=payment_method,
            payer=payer,
            payment_intent__capture_after=utcnow() - timedelta(days=3),
            intent_status=IntentStatus.CANCELLED,
        )

        # Following 3 intents are problematic
        await create_payment_intent(
            cart_payment_repository,
            payment_method=payment_method,
            payer=payer,
            payment_intent__capture_after=utcnow() - timedelta(days=3),
            intent_status=IntentStatus.CAPTURE_FAILED,
        )
        await create_payment_intent(
            cart_payment_repository,
            payment_method=payment_method,
            payer=payer,
            payment_intent__capture_after=utcnow() - timedelta(days=3),
            intent_status=IntentStatus.REQUIRES_CAPTURE,
        )
        await create_payment_intent(
            cart_payment_repository,
            payment_method=payment_method,
            payer=payer,
            payment_intent__capture_after=utcnow() - timedelta(days=3),
            intent_status=IntentStatus.CAPTURING,
        )
        result_after = await cart_payment_repository.count_payment_intents_in_problematic_states(
            problematic_threshold=timedelta(days=2)
        )
        assert (
            result_after - result_before
        ) == 3, "there should be 3 payment intents matched"


class TestUpdatePaymentAndPgpPaymentIntentStatus:
    pytestmark = [pytest.mark.asyncio]

    async def test_success(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
    ):
        pi_pgpi: Optional[
            Tuple[PaymentIntent, PgpPaymentIntent]
        ] = await cart_payment_repository.update_payment_and_pgp_payment_intent_status(
            new_status=IntentStatus.CANCELLED,
            payment_intent_id=payment_intent.id,
            pgp_payment_intent_id=pgp_payment_intent.id,
        )
        assert pi_pgpi
        assert pi_pgpi[0].status == IntentStatus.CANCELLED
        assert pi_pgpi[1].status == IntentStatus.CANCELLED

        pi_pgpi = await cart_payment_repository.update_payment_and_pgp_payment_intent_status(
            new_status=IntentStatus.SUCCEEDED,
            payment_intent_id=payment_intent.id,
            pgp_payment_intent_id=pgp_payment_intent.id,
        )
        assert pi_pgpi

        assert pi_pgpi[0].status == IntentStatus.SUCCEEDED
        assert pi_pgpi[1].status == IntentStatus.SUCCEEDED

    async def test_not_found(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
    ):
        result = await cart_payment_repository.update_payment_and_pgp_payment_intent_status(
            new_status=IntentStatus.CANCELLED,
            payment_intent_id=uuid4(),
            pgp_payment_intent_id=pgp_payment_intent.id,
        )
        assert not result


class TestExistingSuccessChargeForStripeCard:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    async def consumer_charge(self, cart_payment_repository: CartPaymentRepository):
        now = datetime.now(timezone.utc)
        yield await cart_payment_repository.insert_legacy_consumer_charge(
            target_ct_id=1,
            target_id=2,
            consumer_id=1,  # Use of pre-seeded consumer to satisfy FK constraint
            idempotency_key=str(uuid4()),
            is_stripe_connect_based=False,
            country_id=LegacyCountryId.US,
            currency=Currency.USD,
            stripe_customer_id=None,
            total=800,
            original_total=800,
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    async def stripe_charge_succeeded(
        self,
        stripe_card: StripeCardDbEntity,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):

        return await cart_payment_repository.insert_legacy_stripe_charge(
            stripe_id=str(uuid4()),
            card_id=stripe_card.id,
            charge_id=consumer_charge.id,
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.SUCCEEDED,
            idempotency_key=str(uuid4()),
            additional_payment_info="{'test_key': 'test_value'}",
            description="test description",
            error_reason="",
        )

    @pytest.fixture
    async def stripe_charge_failed(
        self,
        stripe_card: StripeCardDbEntity,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        return await cart_payment_repository.insert_legacy_stripe_charge(
            stripe_id=str(uuid4()),
            card_id=stripe_card.id,
            charge_id=consumer_charge.id,
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.FAILED,
            idempotency_key=str(uuid4()),
            additional_payment_info="{'test_key': 'test_value'}",
            description="test description",
            error_reason="",
        )

    @pytest.fixture
    async def stripe_charge_succeeded_with_expired_stripe_card(
        self,
        stripe_card_expired,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        return await cart_payment_repository.insert_legacy_stripe_charge(
            stripe_id=str(uuid4()),
            card_id=stripe_card_expired.id,
            charge_id=consumer_charge.id,
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.SUCCEEDED,
            idempotency_key=str(uuid4()),
            additional_payment_info="{'test_key': 'test_value'}",
            description="test description",
            error_reason="",
        )

    async def test_success_charge_exists(
        self,
        stripe_card: StripeCardDbEntity,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge_succeeded: LegacyStripeCharge,
        stripe_charge_failed: LegacyStripeCharge,
    ):
        assert stripe_charge_succeeded.card_id == stripe_card.id
        assert stripe_charge_failed.card_id == stripe_card.id
        assert await cart_payment_repository.is_stripe_card_valid_and_has_success_charge_record(
            stripe_card_stripe_id=stripe_card.stripe_id
        )

    async def test_no_charge_match(
        self,
        stripe_card: StripeCardDbEntity,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge_succeeded: LegacyStripeCharge,
    ):
        assert stripe_charge_succeeded.card_id == stripe_card.id
        assert not await cart_payment_repository.is_stripe_card_valid_and_has_success_charge_record(
            stripe_card_stripe_id=stripe_card.stripe_id + str(uuid4())
        )

    async def test_no_success_charge(
        self,
        stripe_card: StripeCardDbEntity,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge_failed: LegacyStripeCharge,
    ):
        assert stripe_charge_failed.card_id == stripe_card.id
        assert not await cart_payment_repository.is_stripe_card_valid_and_has_success_charge_record(
            stripe_card_stripe_id=stripe_card.stripe_id
        )

    async def test_success_charge_exists_but_card_expired(
        self,
        stripe_card_expired: StripeCardDbEntity,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge_succeeded_with_expired_stripe_card: LegacyStripeCharge,
    ):
        assert (
            stripe_charge_succeeded_with_expired_stripe_card.card_id
            == stripe_card_expired.id
        )
        is_card_expired = False | (
            int(stripe_card_expired.exp_month) < date.today().month
            and int(stripe_card_expired.exp_year) <= date.today().year
        )
        is_card_expired = is_card_expired | (
            int(stripe_card_expired.exp_year) < date.today().year
        )
        assert is_card_expired
        assert not await cart_payment_repository.is_stripe_card_valid_and_has_success_charge_record(
            stripe_card_stripe_id=stripe_card_expired.stripe_id
        )


class TestListCartPayments:
    pytestmark = [pytest.mark.asyncio]

    async def test_get_cart_payments_by_dd_consumer_id(
        self, payer: PayerDbEntity, cart_payment_repository: CartPaymentRepository
    ):
        client_description = str(uuid4())
        cart_payment = await cart_payment_repository.insert_cart_payment(
            id=uuid4(),
            payer_id=cast(UUID, payer.id),
            amount_original=99,
            amount_total=100,
            client_description=client_description,
            reference_id="99",
            reference_type="88",
            delay_capture=False,
            metadata=None,
            legacy_consumer_id=1,
            legacy_stripe_card_id=1,
            legacy_provider_customer_id="stripe_customer_id",
            legacy_provider_card_id="stripe_card_id",
        )
        cart_payment_list = await cart_payment_repository.get_cart_payments_by_dd_consumer_id(
            input=GetCartPaymentsByConsumerIdInput(dd_consumer_id=1)
        )
        assert cart_payment_list
        assert isinstance(cart_payment_list, List)
        retrieve_inserted_cart_payment = next(
            filter(
                lambda cart_payment: cart_payment.client_description
                == client_description,
                cart_payment_list,
            ),
            None,
        )
        assert retrieve_inserted_cart_payment
        assert retrieve_inserted_cart_payment == cart_payment

    async def test_get_cart_payments_by_reference_id(
        self, payer: PayerDbEntity, cart_payment_repository: CartPaymentRepository
    ):
        client_description = str(uuid4())
        reference_id = str(uuid4())
        cart_payment = await cart_payment_repository.insert_cart_payment(
            id=uuid4(),
            payer_id=cast(UUID, payer.id),
            amount_original=99,
            amount_total=100,
            client_description=client_description,
            reference_id=reference_id,
            reference_type="OrderCart",
            delay_capture=False,
            metadata=None,
            legacy_consumer_id=1,
            legacy_stripe_card_id=1,
            legacy_provider_customer_id="stripe_customer_id",
            legacy_provider_card_id="stripe_card_id",
        )
        cart_payment_list = await cart_payment_repository.get_cart_payments_by_reference_id(
            input=ListCartPaymentsByReferenceId(
                reference_id=reference_id, reference_type="OrderCart"
            )
        )
        assert cart_payment_list
        assert isinstance(cart_payment_list, List)
        retrieve_inserted_cart_payment = next(
            filter(
                lambda cart_payment: cart_payment.client_description
                == client_description,
                cart_payment_list,
            ),
            None,
        )
        assert retrieve_inserted_cart_payment
        assert retrieve_inserted_cart_payment == cart_payment
