from uuid import uuid4

import pytest

from app.commons.types import CountryCode
from app.commons.utils.types import PaymentProvider
from app.payin.core.cart_payment.model import (
    CartPayment,
    PaymentIntent,
    PaymentIntentAdjustmentHistory,
    PgpPaymentIntent,
    PaymentCharge,
    PgpPaymentCharge,
)
from app.payin.core.cart_payment.types import (
    IntentStatus,
    CaptureMethod,
    ConfirmationMethod,
    CartType,
    ChargeStatus,
)
from app.payin.core.exceptions import PaymentIntentCouldNotBeUpdatedError
from app.payin.core.payer.model import Payer
from app.payin.core.payer.types import PayerType
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository, InsertPayerInput
from app.payin.repository.payment_method_repo import (
    PaymentMethodRepository,
    InsertPgpPaymentMethodInput,
    InsertStripeCardInput,
)


@pytest.fixture
async def payer(payer_repository: PayerRepository):
    insert_payer_input = InsertPayerInput(
        id=str(uuid4()), payer_type=PayerType.STORE, country=CountryCode.US
    )
    yield await payer_repository.insert_payer(insert_payer_input)


@pytest.fixture
async def payment_method(payer, payment_method_repository: PaymentMethodRepository):
    insert_payment_method = InsertPgpPaymentMethodInput(
        id=str(uuid4()),
        pgp_code=PaymentProvider.STRIPE.value,
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

    insert_result = await payment_method_repository.insert_payment_method_and_stripe_card(
        insert_payment_method, insert_stripe_card
    )
    yield insert_result[0]


@pytest.fixture
async def cart_payment(cart_payment_repository: CartPaymentRepository, payer: Payer):
    yield await cart_payment_repository.insert_cart_payment(
        id=uuid4(),
        payer_id=payer.id,
        type=CartType.ORDER_CART,
        amount_original=99,
        amount_total=100,
        client_description=None,
        reference_id=99,
        reference_ct_id=88,
        legacy_consumer_id=None,
        delay_capture=False,
    )


@pytest.fixture
async def payment_intent(
    cart_payment_repository: CartPaymentRepository, payer, payment_method
):
    cart_payment_id = uuid4()
    await cart_payment_repository.insert_cart_payment(
        id=cart_payment_id,
        payer_id=payer.id,
        type=CartType.ORDER_CART,
        amount_original=99,
        amount_total=100,
        client_description=None,
        reference_id=99,
        reference_ct_id=88,
        legacy_consumer_id=None,
        delay_capture=False,
    )

    payment_intent = await cart_payment_repository.insert_payment_intent(
        id=uuid4(),
        cart_payment_id=cart_payment_id,
        idempotency_key=f"ik_{uuid4()}",
        amount_initiated=100,
        amount=200,
        application_fee_amount=100,
        country=CountryCode.US,
        currency="USD",
        capture_method=CaptureMethod.MANUAL,
        confirmation_method=ConfirmationMethod.MANUAL,
        status=IntentStatus.REQUIRES_CAPTURE,
        statement_descriptor=None,
        capture_after=None,
        payment_method_id=payment_method.id,
    )
    yield payment_intent


@pytest.fixture
async def pgp_payment_intent(
    cart_payment_repository: CartPaymentRepository, payment_intent: PaymentIntent
):
    yield await cart_payment_repository.insert_pgp_payment_intent(
        id=uuid4(),
        payment_intent_id=payment_intent.id,
        idempotency_key=str(uuid4()),
        provider=PaymentProvider.STRIPE,
        payment_method_resource_id="pm_test",
        customer_resource_id=None,
        currency="USD",
        amount=500,
        application_fee_amount=None,
        payout_account_id=None,
        capture_method=CaptureMethod.MANUAL,
        confirmation_method=ConfirmationMethod.MANUAL,
        status=IntentStatus.REQUIRES_CAPTURE,
        statement_descriptor="Test",
    )


@pytest.fixture
async def payment_charge(
    cart_payment_repository: CartPaymentRepository, payment_intent: PaymentIntent
):
    yield await cart_payment_repository.insert_payment_charge(
        id=uuid4(),
        payment_intent_id=payment_intent.id,
        provider=PaymentProvider.STRIPE,
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
        provider=PaymentProvider.STRIPE,
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
    @pytest.mark.skip("fix this to not relying on forcerollback")
    async def test_find_uncaptured_payment_intents_when_none_exist(
        self, cart_payment_repository: CartPaymentRepository
    ):
        uncaptured_payment_intents = await cart_payment_repository.find_payment_intents_with_status(
            IntentStatus.REQUIRES_CAPTURE
        )
        assert uncaptured_payment_intents == []

    @pytest.mark.asyncio
    @pytest.mark.skip("fix this to not relying on forcerollback")
    async def test_find_uncaptured_payment_intents_when_one_exists(
        self, cart_payment_repository: CartPaymentRepository, payment_intent
    ):
        uncaptured_payment_intents = await cart_payment_repository.find_payment_intents_with_status(
            IntentStatus.REQUIRES_CAPTURE
        )
        uncaptured_payment_intent_ids = [pi.id for pi in uncaptured_payment_intents]
        assert uncaptured_payment_intent_ids == [payment_intent.id]

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
            amount_capturable=payment_intent.amount_capturable,
            amount_received=payment_intent.amount_received,
            application_fee_amount=payment_intent.application_fee_amount,
            capture_method=payment_intent.capture_method,
            confirmation_method=payment_intent.confirmation_method,
            country=payment_intent.country,
            currency=payment_intent.currency,
            status=payment_intent.status,
            statement_descriptor=payment_intent.statement_descriptor,
            payment_method_id=payment_intent.payment_method_id,
            created_at=payment_intent.created_at,
            updated_at=result.updated_at,  # Don't know generated date ahead of time
            captured_at=payment_intent.captured_at,
            cancelled_at=payment_intent.cancelled_at,
        )
        assert result == expected_result


class TestPaymentIntentAdjustmentHistory:
    @pytest.mark.asyncio
    async def test_insert_history(
        self,
        cart_payment_repository: CartPaymentRepository,
        cart_payment: CartPayment,
        payment_method,
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
            confirmation_method=ConfirmationMethod.MANUAL,
            status=IntentStatus.REQUIRES_CAPTURE,
            statement_descriptor=None,
            capture_after=None,
            payment_method_id=payment_method.id,
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
        )

        expected_adjustment = PaymentIntentAdjustmentHistory(
            id=id,
            payer_id=cart_payment.payer_id,
            payment_intent_id=payment_intent.id,
            amount=payment_intent.amount + 100,
            amount_original=payment_intent.amount,
            amount_delta=100,
            currency=payment_intent.currency,
            created_at=result.created_at,  # Do not know exact created_at ahead of time
        )

        assert result == expected_adjustment


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
            provider=pgp_payment_intent.provider,
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
            confirmation_method=pgp_payment_intent.confirmation_method,
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
            provider=pgp_payment_intent.provider,
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
            confirmation_method=pgp_payment_intent.confirmation_method,
            created_at=pgp_payment_intent.created_at,
            updated_at=result.updated_at,  # Don't know exact date ahead of time
            captured_at=pgp_payment_intent.captured_at,
            cancelled_at=pgp_payment_intent.cancelled_at,
        )
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
            provider=PaymentProvider.STRIPE,
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
            provider=PaymentProvider.STRIPE,
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
            provider=payment_charge.provider,
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
            provider=payment_charge.provider,
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
            provider=payment_charge.provider,
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
            provider=PaymentProvider.STRIPE,
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
            provider=PaymentProvider.STRIPE,
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
            provider=pgp_payment_charge.provider,
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
            provider=pgp_payment_charge.provider,
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
            provider=pgp_payment_charge.provider,
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
        payment_intent = await cart_payment_repository.update_payment_intent_status(
            payment_intent.id,
            IntentStatus.CAPTURING.value,
            IntentStatus.REQUIRES_CAPTURE.value,
        )
        assert payment_intent.status == IntentStatus.CAPTURING.value

    @pytest.mark.asyncio
    async def test_failure_returns_nothing(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        with pytest.raises(PaymentIntentCouldNotBeUpdatedError):
            await cart_payment_repository.update_payment_intent_status(
                payment_intent.id, IntentStatus.CAPTURING.value, IntentStatus.INIT.value
            )


class TestCartPayment:
    @pytest.mark.asyncio
    async def test_get_cart_payment_by_id(
        self, cart_payment_repository: CartPaymentRepository, cart_payment: CartPayment
    ):
        # No result
        result = await cart_payment_repository.get_cart_payment_by_id(
            cart_payment_id=uuid4()
        )
        assert result is None

        # Match
        result = await cart_payment_repository.get_cart_payment_by_id(
            cart_payment_id=cart_payment.id
        )
        assert result == cart_payment
