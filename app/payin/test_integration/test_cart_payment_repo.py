from datetime import datetime, timedelta
from typing import cast
from uuid import uuid4, UUID

import pytest
from IPython.utils.tz import utcnow

from app.commons.types import CountryCode, LegacyCountryId, Currency
from app.commons.utils.types import PaymentProvider
from app.payin.core.cart_payment.model import (
    CartPayment,
    CorrelationIds,
    LegacyPayment,
    LegacyConsumerCharge,
    LegacyStripeCharge,
    PaymentIntent,
    PaymentIntentAdjustmentHistory,
    PgpPaymentIntent,
    PaymentCharge,
    PgpPaymentCharge,
)
from app.payin.core.cart_payment.types import (
    IntentStatus,
    CaptureMethod,
    ChargeStatus,
    LegacyStripeChargeStatus,
    LegacyConsumerChargeId,
)
from app.payin.core.exceptions import PaymentIntentCouldNotBeUpdatedError
from app.payin.core.payer.model import Payer
from app.payin.core.payer.types import PayerType
from app.payin.core.types import PgpPayerResourceId, PgpPaymentMethodResourceId
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
    insert_pm_result = await payment_method_repository.insert_pgp_payment_method(
        insert_payment_method
    )
    await payment_method_repository.insert_stripe_card(insert_stripe_card)

    yield insert_pm_result


@pytest.fixture
async def cart_payment(cart_payment_repository: CartPaymentRepository, payer: Payer):
    yield await cart_payment_repository.insert_cart_payment(
        id=uuid4(),
        payer_id=cast(UUID, payer.id),
        amount_original=99,
        amount_total=100,
        client_description=None,
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
    payer,
    payment_method,
    payment_intent__capture_after,
):
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
        status=IntentStatus.REQUIRES_CAPTURE,
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
    return datetime(2019, 1, 1)


@pytest.fixture
async def payment_intent(
    cart_payment_repository: CartPaymentRepository,
    payer,
    payment_method,
    payment_intent__capture_after: datetime,
):
    yield await create_payment_intent(
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
        provider=PaymentProvider.STRIPE,
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
        assert result == (None, None)

        # Match
        result = await cart_payment_repository.get_cart_payment_by_id(
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
    async def test_insert_cart_payment(
        self, cart_payment_repository: CartPaymentRepository, payer: Payer
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


class TestLegacyCharges:
    @pytest.fixture
    async def consumer_charge(self, cart_payment_repository: CartPaymentRepository):
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
        )

    @pytest.fixture
    async def stripe_charge(
        self,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge: LegacyConsumerCharge,
    ):
        yield await cart_payment_repository.insert_legacy_stripe_charge(
            stripe_id=str(uuid4()),
            card_id=None,
            charge_id=consumer_charge.id,
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.SUCCEEDED.value,
            idempotency_key=str(uuid4()),
            additional_payment_info="{'test_key': 'test_value'}",
            description="test description",
        )

    @pytest.mark.asyncio
    async def test_insert_legacy_consumer_charge(
        self, cart_payment_repository: CartPaymentRepository
    ):
        idempotency_key = str(uuid4())
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
        )

        assert result == expected_consumer_charge

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
            status=LegacyStripeChargeStatus.SUCCEEDED.value,
            idempotency_key=idempotency_key,
            additional_payment_info="{'test_key': 'test_value'}",
            description="Test description",
        )

        expected_stripe_charge = LegacyStripeCharge(
            id=result.id,  # Generated
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.SUCCEEDED.value,
            error_reason=None,
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
    async def test_update_legacy_stripe_charge_refund(
        self,
        cart_payment_repository: CartPaymentRepository,
        stripe_charge: LegacyStripeCharge,
    ):
        result = await cart_payment_repository.update_legacy_stripe_charge_refund(
            stripe_id=stripe_charge.stripe_id,
            amount_refunded=200,
            refunded_at=datetime.now(),
        )

        expected_result = stripe_charge
        expected_result.amount_refunded = 200
        expected_result.refunded_at = result.refunded_at
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
            currency="cad",
            status=LegacyStripeChargeStatus.SUCCEEDED,
        )

        expected_result = stripe_charge
        expected_result.stripe_id = f"stripe-{stripe_charge.id}"
        expected_result.amount = 450
        expected_result.amount_refunded = 300
        expected_result.currency = "cad"
        expected_result.status = LegacyStripeChargeStatus.SUCCEEDED
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
        assert result == expected_result

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


class TestFindPaymentIntentsThatRequireCapture:
    @pytest.mark.asyncio
    async def test_returns_batches(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_intent: PaymentIntent,
    ):
        results = cart_payment_repository.find_payment_intents_that_require_capture(
            cutoff=datetime(2016, 1, 1)
        )
        ids = [i.id async for i in results]
        assert payment_intent.id in ids


class TestCountPaymentIntentsThatRequireCapture:
    @pytest.mark.asyncio
    async def test_success(
        self,
        cart_payment_repository: CartPaymentRepository,
        payment_method,
        payment_intent: PaymentIntent,
        payer: Payer,
        payment_intent__capture_after: datetime,
    ):
        # Our databases are not data-less for each test run, so we need to count the payment intents before and after
        # to write this test. This is so dirty!
        result_before = await cart_payment_repository.count_payment_intents_that_require_capture(
            problematic_threshold=timedelta(days=2)
        )
        await create_payment_intent(
            cart_payment_repository,
            payment_method=payment_method,
            payer=payer,
            payment_intent__capture_after=utcnow() - timedelta(days=3),
        )
        result_after = await cart_payment_repository.count_payment_intents_that_require_capture(
            problematic_threshold=timedelta(days=2)
        )
        assert (
            result_after - result_before
        ) == 1, "there should be one payment intent matched"
