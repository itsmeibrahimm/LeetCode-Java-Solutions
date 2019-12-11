from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import pytest

from app.commons.types import CountryCode, Currency, PgpCode
from app.payin.core.cart_payment.model import (
    CartPayment,
    CorrelationIds,
    LegacyConsumerCharge,
    LegacyPayment,
    LegacyStripeCharge,
    PaymentIntent,
    PgpPaymentIntent,
)
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.types import IntentStatus, LegacyStripeChargeStatus
from app.payin.core.exceptions import CartPaymentCreateError
from app.payin.core.payer.model import Payer
from app.payin.core.payer.v1.processor import PayerProcessorV1
from app.payin.core.payment_method.model import PaymentMethod
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.payment_method.types import LegacyPaymentMethodInfo
from app.payin.repository.cart_payment_repo import CartPaymentRepository


@dataclass
class PgpPaymentIntentState:
    status: IntentStatus
    amount: int
    amount_received: Optional[int]
    amount_capturable: Optional[int]


@dataclass
class StripeChargeState:
    status: LegacyStripeChargeStatus
    amount: int
    amount_refunded: int
    error_reason: str


@dataclass
class PaymentIntentState:
    status: IntentStatus
    amount: int
    pgp_payment_intent_state: PgpPaymentIntentState
    stripe_charge_state: StripeChargeState


@dataclass
class CartPaymentState:
    description: str
    initial_amount: int
    amount_delta_update: Optional[int]
    expected_amount: int
    capture_intents: bool
    delay_capture: bool
    payment_intent_states: List[PaymentIntentState]

    def __post_init__(self):
        if self.amount_delta_update and self.capture_intents:
            raise ValueError(
                "only 1 of capture_intents and amount_delta_update can be specified in a single state change"
            )


class CartPaymentTestBase(ABC):
    def _verify_payment_intent_state(
        self,
        actual_payment_intent: PaymentIntent,
        expected_payment_intent_state: PaymentIntentState,
    ):
        assert actual_payment_intent
        assert (
            actual_payment_intent.amount == expected_payment_intent_state.amount
        ), "payment_intent amount mismatch"
        assert (
            actual_payment_intent.status == expected_payment_intent_state.status
        ), "payment_intent status mismatch"

    def _verify_pgp_payment_intent_state(
        self,
        actual_pgp_payment_intent: PgpPaymentIntent,
        expected_pgp_payment_intent_state: PgpPaymentIntentState,
    ):
        assert (
            actual_pgp_payment_intent.amount == expected_pgp_payment_intent_state.amount
        ), "pgp_payment_intent amount mismatch"
        assert (
            actual_pgp_payment_intent.amount_capturable
            == expected_pgp_payment_intent_state.amount_capturable
        ), "pgp_payment_intent amount_capturable mismatch"
        assert (
            actual_pgp_payment_intent.amount_received
            == expected_pgp_payment_intent_state.amount_received
        ), "pgp_payment_intent amount_received mismatch"

    def _verify_consumer_charge_state(
        self, actual_consumer_charge: LegacyConsumerCharge, expected_amount: int
    ):
        assert (
            actual_consumer_charge.original_total == expected_amount
        ), "consumer charge amount always = init cart payment amount"

    def _verify_stripe_charge_state(
        self,
        actual_stripe_charge: LegacyStripeCharge,
        expected_payment_intent_state: StripeChargeState,
    ):
        assert (
            actual_stripe_charge.amount == expected_payment_intent_state.amount
        ), "stripe charge amount mismatch"
        assert (
            actual_stripe_charge.status == expected_payment_intent_state.status
        ), "stripe charge status mismatch"
        assert (
            actual_stripe_charge.amount_refunded
            == expected_payment_intent_state.amount_refunded
        ), "stripe charge amount_refunded mismatch"
        assert (
            actual_stripe_charge.error_reason
            == expected_payment_intent_state.error_reason
        ), "stripe charge error_reason mismatch"
        assert actual_stripe_charge.stripe_id, "stripe charge resource id missing"

    async def _test_cart_payment_creation_error(
        self,
        cart_payment_state: CartPaymentState,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        # Try to create cart payment, requiring that failure happens
        idempotency_key = str(uuid4())
        with pytest.raises(CartPaymentCreateError):
            await self._prepare_cart_payment(
                payer=payer,
                payment_method=payment_method,
                delay_capture=cart_payment_state.delay_capture,
                cart_payment_processor=cart_payment_processor,
                idempotency_key=idempotency_key,
            )

        # Verify intent, pgp intent
        payment_intent = await cart_payment_repository.get_payment_intent_by_idempotency_key_from_primary(
            idempotency_key=idempotency_key
        )

        assert payment_intent
        self._verify_payment_intent_state(
            payment_intent, cart_payment_state.payment_intent_states[0]
        )

        all_intents = await cart_payment_repository.get_payment_intents_by_cart_payment_id_from_primary(
            cart_payment_id=payment_intent.cart_payment_id
        )
        assert len(all_intents) == 1
        assert all_intents[0].id == payment_intent.id

        pgp_payment_intents = await cart_payment_repository.list_pgp_payment_intents_from_primary(
            payment_intent.id
        )
        assert len(pgp_payment_intents) == 1
        self._verify_pgp_payment_intent_state(
            pgp_payment_intents[0],
            cart_payment_state.payment_intent_states[0].pgp_payment_intent_state,
        )

        # Verify legacy consumer charge, stripe charge
        consumer_charge, stripe_charge = await cart_payment_processor.legacy_payment_interface.find_existing_payment_charge(
            charge_id=payment_intent.legacy_consumer_charge_id,
            idempotency_key=payment_intent.idempotency_key,
        )

        assert consumer_charge, "consumer charge not found!"
        assert stripe_charge, "stripe charge not found!"

        self._verify_consumer_charge_state(
            consumer_charge, cart_payment_state.payment_intent_states[0].amount
        )
        self._verify_stripe_charge_state(
            stripe_charge,
            cart_payment_state.payment_intent_states[0].stripe_charge_state,
        )

    async def _test_cart_payment_state_transition(
        self,
        cart_payment_states: List[CartPaymentState],
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ) -> CartPayment:
        # 1. Prepare and verify initial CartPayment:
        init_cart_payment_state = cart_payment_states[0]
        init_cart_payment = await self._prepare_cart_payment(
            payer=payer,
            payment_method=payment_method,
            delay_capture=init_cart_payment_state.delay_capture,
            cart_payment_processor=cart_payment_processor,
            idempotency_key=str(uuid4()),
        )

        assert (
            init_cart_payment.amount == init_cart_payment_state.expected_amount
        ), f"cart payment amount as expected {init_cart_payment_state}"

        init_payment_intents = await cart_payment_repository.get_payment_intents_by_cart_payment_id_from_primary(
            init_cart_payment.id
        )

        assert (
            len(init_payment_intents) == 1
        ), f"only expect 1 initial payment_intents {init_cart_payment_state}"
        assert (
            len(init_cart_payment_state.payment_intent_states) == 1
        ), f"only expect single payment intent for init creating {init_cart_payment_state}"
        init_payment_intent = init_payment_intents[0]

        consumer_charge_id = init_payment_intent.legacy_consumer_charge_id

        # 2. Now update per input and verify after each update
        for new_cart_payment_state in cart_payment_states:
            try:
                await self._update_and_verify_cart_payment_states(
                    init_cart_payment=init_cart_payment,
                    consumer_charge_id=consumer_charge_id,
                    new_cart_payment_state=new_cart_payment_state,
                    cart_payment_processor=cart_payment_processor,
                    cart_payment_repository=cart_payment_repository,
                )
            except AssertionError as e:
                raise AssertionError(
                    f"Failed cart payment state change: {new_cart_payment_state}, exception {e}"
                ) from e

        latest_cart_payment, _ = await cart_payment_repository.get_cart_payment_by_id_from_primary(
            init_cart_payment.id
        )
        assert latest_cart_payment
        return latest_cart_payment

    async def _update_and_verify_cart_payment_states(
        self,
        init_cart_payment: CartPayment,
        consumer_charge_id: int,
        new_cart_payment_state: CartPaymentState,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
    ):
        pre_update_payment_intents = await cart_payment_repository.get_payment_intents_by_cart_payment_id_from_primary(
            cart_payment_id=init_cart_payment.id
        )
        id_to_pre_update_payment_intents = {
            pi.id: pi for pi in pre_update_payment_intents
        }

        # Presence of idempotency_key means whether there is adjustment
        adjustment_idempotency_key = None

        if new_cart_payment_state.amount_delta_update:
            cart_payment_pre_update, _ = await cart_payment_repository.get_cart_payment_by_id_from_primary(
                init_cart_payment.id
            )
            assert (
                cart_payment_pre_update
            ), "expect cart_payment already exists before update!"
            amount_delta_to_update = new_cart_payment_state.amount_delta_update
            adjustment_idempotency_key = str(uuid4())
            await self._update_cart_payment(
                cart_payment_processor=cart_payment_processor,
                existing_cart_payment=cart_payment_pre_update,
                idempotency_key=adjustment_idempotency_key,
                payer_id=cart_payment_pre_update.payer_id,
                delta_amount=amount_delta_to_update,
                consumer_charge_id=consumer_charge_id,
            )
        elif (
            new_cart_payment_state.capture_intents
            and new_cart_payment_state.delay_capture
        ):
            await self._capture_intents(
                cart_payment_repository=cart_payment_repository,
                cart_payment_processor=cart_payment_processor,
            )

        updated_cart_payment, _ = await cart_payment_repository.get_cart_payment_by_id_from_primary(
            init_cart_payment.id
        )

        assert isinstance(updated_cart_payment, CartPayment)
        assert (
            updated_cart_payment.amount == new_cart_payment_state.expected_amount
        ), "updated_cart_payment amount mismatch"

        updated_payment_intents = await cart_payment_repository.get_payment_intents_by_cart_payment_id_from_primary(
            updated_cart_payment.id
        )
        updated_payment_intents.sort(key=lambda pi: pi.created_at)

        for payment_intent, payment_intent_state in zip(
            updated_payment_intents, new_cart_payment_state.payment_intent_states
        ):
            # verify new path
            self._verify_payment_intent_state(payment_intent, payment_intent_state)
            pgp_payment_intents = await cart_payment_repository.list_pgp_payment_intents_from_primary(
                payment_intent.id
            )

            # when there is payment_intent update, verify adjustment history
            if (
                payment_intent.id in id_to_pre_update_payment_intents
                and payment_intent.amount
                != id_to_pre_update_payment_intents[payment_intent.id].amount
            ):
                assert (
                    adjustment_idempotency_key
                ), "expect idempotency key when updates happen"
                payment_intent_adjustment_history = await cart_payment_repository.get_payment_intent_adjustment_history_from_primary(
                    payment_intent.id, adjustment_idempotency_key
                )
                pre_update_payment_intent: PaymentIntent = id_to_pre_update_payment_intents[
                    payment_intent.id
                ]
                if new_cart_payment_state.delay_capture:
                    # TODO Fix this to work for the immediate capture case, where a record is added for the refund of past intents
                    # TODO Verify expected refund state
                    assert (
                        payment_intent_adjustment_history
                    ), "payment_intent_adjustment_history not found!"
                    assert (
                        payment_intent_adjustment_history.amount_original
                        == pre_update_payment_intent.amount
                    ), "payment_intent_adjustment_history amount_original mismatch"
                    assert (
                        payment_intent_adjustment_history.amount_delta
                        == payment_intent.amount - pre_update_payment_intent.amount
                    ), "payment_intent_adjustment_history amount_delta mismatch"
                    assert (
                        payment_intent_adjustment_history.amount
                        == payment_intent.amount
                    ), "payment_intent_adjustment_history amount mismatch"

            # verify pgp_payment_intents
            assert (
                len(pgp_payment_intents) == 1
            ), "number of pgp_payment_intent mismatch"
            self._verify_pgp_payment_intent_state(
                pgp_payment_intents[0], payment_intent_state.pgp_payment_intent_state
            )

            # verify legacy path
            consumer_charge, stripe_charge = await cart_payment_processor.legacy_payment_interface.find_existing_payment_charge(
                charge_id=payment_intent.legacy_consumer_charge_id,
                idempotency_key=payment_intent.idempotency_key,
            )
            assert consumer_charge, "consumer charge not found!"
            assert stripe_charge, "stripe charge not found!"
            self._verify_consumer_charge_state(
                consumer_charge, init_cart_payment.amount
            )
            self._verify_stripe_charge_state(
                stripe_charge, payment_intent_state.stripe_charge_state
            )

    async def _capture_intents(
        self,
        cart_payment_repository: CartPaymentRepository,
        cart_payment_processor: CartPaymentProcessor,
    ):

        # TODO ideally should just use "capture_uncapture_payment_intents" here to run in job pool
        # though this could occasionally cause db transaction cannot be properly closed likely due to
        # some unknown race condition. need to investigate and revise.
        utcnow = datetime.now(timezone.utc)
        uncaptured_payment_intents = cart_payment_repository.find_payment_intents_that_require_capture(
            capturable_before=utcnow, earliest_capture_after=utcnow - timedelta(hours=1)
        )

        async for payment_intent in uncaptured_payment_intents:
            # skip payment_intents created by other integration tests, which, in prod scenario shouldn't happen
            is_well_formed = await self._is_wellformed_payment_intent(
                payment_intent, cart_payment_repository
            )
            if is_well_formed:
                await cart_payment_processor.capture_payment(payment_intent)

    async def _is_wellformed_payment_intent(
        self,
        payment_intent: PaymentIntent,
        cart_payment_repository: CartPaymentRepository,
    ) -> bool:
        if payment_intent.created_at < datetime.now(timezone.utc) - timedelta(days=7):
            return False

        pgp_payment_intents: List[
            PgpPaymentIntent
        ] = await cart_payment_repository.list_pgp_payment_intents_from_primary(
            payment_intent.id
        )
        if not pgp_payment_intents:
            return False
        for pgp_payment_intent in pgp_payment_intents:
            if pgp_payment_intent.status != payment_intent.status:
                return False
            if not pgp_payment_intent.resource_id:
                return False
        return True

    @abstractmethod
    async def _prepare_cart_payment(
        self,
        payer: Payer,
        payment_method: PaymentMethod,
        delay_capture: bool,
        cart_payment_processor: CartPaymentProcessor,
        idempotency_key: str,
    ) -> CartPayment:
        pass

    @abstractmethod
    async def _update_cart_payment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        existing_cart_payment: CartPayment,
        consumer_charge_id: int,
        idempotency_key: str,
        payer_id: Optional[UUID],
        delta_amount: int,
    ):
        pass


class CartPaymentTest(CartPaymentTestBase):
    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    @pytest.fixture
    async def payer(self, payer_processor_v1: PayerProcessorV1) -> Payer:
        return await payer_processor_v1.create_payer(
            dd_payer_id="1",
            payer_type="store",
            email=f"{str(uuid4())}@doordash.com)",
            country=CountryCode.US,
            description="test-payer",
        )

    @pytest.fixture
    async def payment_method(
        self, payment_method_processor: PaymentMethodProcessor, payer: Payer
    ) -> PaymentMethod:
        return await payment_method_processor.create_payment_method(
            pgp_code=PgpCode.STRIPE,
            token="tok_mastercard",
            set_default=True,
            is_scanned=True,
            is_active=True,
            payer_id=payer.id,
        )

    async def _prepare_cart_payment(
        self,
        payer: Payer,
        payment_method: PaymentMethod,
        delay_capture: bool,
        cart_payment_processor: CartPaymentProcessor,
        idempotency_key: str,
    ) -> CartPayment:
        request = CartPayment(
            id=uuid4(),
            amount=1000,
            payer_id=payer.id,
            payment_method_id=payment_method.id,
            delay_capture=delay_capture,
            correlation_ids=CorrelationIds(reference_id="123", reference_type="3"),
            metadata={},
            client_description="client_description",
            payer_statement_description="description",
        )
        created = await cart_payment_processor.create_payment(
            request_cart_payment=request,
            idempotency_key=idempotency_key,
            currency=Currency.USD,
            payment_country=CountryCode(payer.country),
        )
        return created

    async def _update_cart_payment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        existing_cart_payment: CartPayment,
        consumer_charge_id: int,
        idempotency_key: str,
        payer_id: Optional[UUID],
        delta_amount: int,
    ):
        assert payer_id
        await cart_payment_processor.update_payment(
            idempotency_key=idempotency_key,
            cart_payment_id=existing_cart_payment.id,
            payer_id=payer_id,
            amount=delta_amount + existing_cart_payment.amount,
            client_description="adjust cart payment description",
            split_payment=None,
        )


class CartPaymentLegacyTest(CartPaymentTestBase):
    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    @pytest.fixture
    async def payer(self, payer_processor_v1: PayerProcessorV1) -> Payer:
        return await payer_processor_v1.create_payer(
            dd_payer_id=f"{str(int(datetime.utcnow().timestamp()))}",
            payer_type="store",
            email=f"{str(uuid4())}@doordash.com)",
            country=CountryCode.US,
            description="test-payer",
        )

    @pytest.fixture
    async def payment_method(
        self, payment_method_processor: PaymentMethodProcessor, payer: Payer
    ) -> PaymentMethod:
        assert payer.payment_gateway_provider_customers
        return await payment_method_processor.create_payment_method(
            pgp_code=PgpCode.STRIPE,
            token="tok_mastercard",
            set_default=True,
            is_scanned=True,
            is_active=True,
            legacy_payment_method_info=LegacyPaymentMethodInfo(
                country=CountryCode.US,
                stripe_customer_id=payer.payment_gateway_provider_customers[
                    0
                ].payment_provider_customer_id,
                dd_stripe_customer_id=payer.dd_stripe_customer_id,
            ),
        )

    async def _prepare_cart_payment(
        self,
        payer: Payer,
        payment_method: PaymentMethod,
        delay_capture: bool,
        cart_payment_processor: CartPaymentProcessor,
        idempotency_key: str,
    ) -> CartPayment:
        request = CartPayment(
            id=uuid4(),
            amount=1000,
            payment_method_id=payment_method.id,
            delay_capture=delay_capture,
            correlation_ids=CorrelationIds(reference_id="123", reference_type="3"),
            metadata={},
            client_description="client_description",
            payer_statement_description="description",
        )

        assert payer.payment_gateway_provider_customers

        created, _ = await cart_payment_processor.legacy_create_payment(
            request_cart_payment=request,
            idempotency_key=idempotency_key,
            legacy_payment=LegacyPayment(
                dd_consumer_id=1,
                dd_country_id=1,
                dd_stripe_card_id=payment_method.dd_stripe_card_id,
                stripe_customer_id=payer.payment_gateway_provider_customers[
                    0
                ].payment_provider_customer_id,
                stripe_card_id=payment_method.payment_gateway_provider_details.payment_method_id,
            ),
            currency=Currency.USD,
            payment_country=CountryCode(payer.country),
            payer_country=CountryCode(payer.country),
        )
        return created

    async def _update_cart_payment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        existing_cart_payment: CartPayment,
        consumer_charge_id: int,
        idempotency_key: str,
        payer_id: Optional[UUID],
        delta_amount: int,
    ):
        await cart_payment_processor.update_payment_for_legacy_charge(
            idempotency_key=idempotency_key,
            dd_charge_id=consumer_charge_id,
            amount=delta_amount,
            client_description="adjust cart payment description",
            dd_additional_payment_info=None,
            split_payment=None,
        )
