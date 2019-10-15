from abc import ABC, abstractmethod
from datetime import datetime
from uuid import uuid4, UUID

import pytest

from app.commons.context.app_context import AppContext
from app.commons.types import CountryCode, Currency, PgpCode
from app.conftest import StripeAPISettings
from app.payin.core.cart_payment.model import (
    CartPayment,
    CorrelationIds,
    LegacyPayment,
    PaymentIntent,
)
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.types import IntentStatus
from app.payin.core.payer.model import Payer
from app.payin.core.payer.v1.processor import PayerProcessorV1
from app.payin.core.payment_method.model import PaymentMethod
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.repository.cart_payment_repo import CartPaymentRepository


class CapturePaymentIntentTestBase(ABC):
    async def _test_capture_after_cart_payment_creation_without_adjustment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):

        cart_payment = await self._prepare_cart_payment(
            payer=payer,
            payment_method=payment_method,
            cart_payment_processor=cart_payment_processor,
        )

        """
        [Initial creation]
        - 1 payment_intent with status=require_capture
        - 1 pgp_payment_intent with status=require_capture
        """
        # Verify payment_intent status pre capture
        init_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        assert len(init_payment_intents) == 1
        assert init_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE

        # Verify pgp_payment_intent status pre capture
        init_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            init_payment_intents[0].id
        )
        assert len(init_pgp_payment_intents) == 1
        assert init_pgp_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE

        """
        [Capture]
        - 1 payment_intent with status=success
        - 1 pgp_payment_intent with status=success
        """
        await self._capture_intents(
            cart_payment_processor=cart_payment_processor,
            cart_payment_repository=cart_payment_repository,
        )

        # Verify payment_intent status post capture
        post_cap_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        assert len(post_cap_payment_intents) == 1
        assert init_payment_intents[0].id == post_cap_payment_intents[0].id
        assert post_cap_payment_intents[0].status == IntentStatus.SUCCEEDED

        # Verify pgp_payment_intent status post capture
        post_cap_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            post_cap_payment_intents[0].id
        )
        assert len(post_cap_pgp_payment_intents) == 1
        assert init_pgp_payment_intents[0].id == post_cap_pgp_payment_intents[0].id
        assert post_cap_pgp_payment_intents[0].status == IntentStatus.SUCCEEDED

    async def _test_capture_after_cart_payment_creation_with_partial_refund(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):

        cart_payment = await self._prepare_cart_payment(
            payer=payer,
            payment_method=payment_method,
            cart_payment_processor=cart_payment_processor,
        )

        """
        [Initial creation]
        - 1 payment_intent with status=require_capture
        - 1 pgp_payment_intent with status=require_capture
        """
        # Verify payment_intent status pre capture
        init_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        assert len(init_payment_intents) == 1
        assert init_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE

        # Verify pgp_payment_intent status pre capture
        init_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            init_payment_intents[0].id
        )
        assert len(init_pgp_payment_intents) == 1
        assert init_pgp_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE

        """
        [Adjustment - partial refund]
        - 1 payment_intent with status=require_capture
        - 1 pgp_payment_intent with status=require_capture
        - both payment_intent and pgp_payment_intent amount reflect updates
        """
        delta_amount = -int(cart_payment.amount / 2)
        assert payer.id

        await self._update_cart_payment(
            cart_payment_processor=cart_payment_processor,
            existing_cart_payment=cart_payment,
            initial_payment_intent=init_payment_intents[0],
            idempotency_key=str(uuid4()),
            payer_id=payer.id,
            delta_amount=delta_amount,
        )

        post_adj_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        assert len(post_adj_payment_intents) == 1
        assert post_adj_payment_intents[0].id == init_payment_intents[0].id
        assert post_adj_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE
        assert (
            post_adj_payment_intents[0].amount
            == init_payment_intents[0].amount + delta_amount
        )

        post_adj_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            post_adj_payment_intents[0].id
        )
        assert len(post_adj_pgp_payment_intents) == 1
        assert post_adj_pgp_payment_intents[0].id == init_pgp_payment_intents[0].id
        assert post_adj_pgp_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE
        assert (
            post_adj_pgp_payment_intents[0].amount
            == init_pgp_payment_intents[0].amount + delta_amount
        )

        """
        [Capture]
        - 1 payment_intent with status=success
        - 1 pgp_payment_intent with status=success
        """
        await self._capture_intents(
            cart_payment_processor=cart_payment_processor,
            cart_payment_repository=cart_payment_repository,
        )

        # Verify payment_intent status post capture
        post_cap_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        assert len(post_cap_payment_intents) == 1
        assert init_payment_intents[0].id == post_cap_payment_intents[0].id
        assert post_cap_payment_intents[0].status == IntentStatus.SUCCEEDED

        # Verify pgp_payment_intent status post capture
        post_cap_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            post_cap_payment_intents[0].id
        )
        assert len(post_cap_pgp_payment_intents) == 1
        assert init_pgp_payment_intents[0].id == post_cap_pgp_payment_intents[0].id
        assert post_cap_pgp_payment_intents[0].status == IntentStatus.SUCCEEDED

    async def _test_capture_after_cart_payment_creation_with_full_refund(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):

        cart_payment = await self._prepare_cart_payment(
            payer=payer,
            payment_method=payment_method,
            cart_payment_processor=cart_payment_processor,
        )

        """
        [Initial creation]
        - 1 payment_intent with status=require_capture
        - 1 pgp_payment_intent with status=require_capture
        """
        # Verify payment_intent status pre capture
        init_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        assert len(init_payment_intents) == 1
        assert init_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE

        # Verify pgp_payment_intent status pre capture
        init_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            init_payment_intents[0].id
        )
        assert len(init_pgp_payment_intents) == 1
        assert init_pgp_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE

        """
        [Adjustment - full refund]
        - 1 payment_intent with status=canceled
        - 1 pgp_payment_intent with status=canceled
        - both payment_intent and pgp_payment_intent amount reflect updates
        """
        delta_amount = -cart_payment.amount
        assert payer.id
        await self._update_cart_payment(
            cart_payment_processor=cart_payment_processor,
            existing_cart_payment=cart_payment,
            initial_payment_intent=init_payment_intents[0],
            idempotency_key=str(uuid4()),
            payer_id=payer.id,
            delta_amount=delta_amount,
        )

        post_adj_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        assert len(post_adj_payment_intents) == 1
        assert post_adj_payment_intents[0].id == init_payment_intents[0].id
        assert post_adj_payment_intents[0].status == IntentStatus.CANCELLED
        assert post_adj_payment_intents[0].amount == 0

        post_adj_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            post_adj_payment_intents[0].id
        )
        assert len(post_adj_pgp_payment_intents) == 1
        assert post_adj_pgp_payment_intents[0].id == init_pgp_payment_intents[0].id
        assert post_adj_pgp_payment_intents[0].status == IntentStatus.CANCELLED
        assert post_adj_pgp_payment_intents[0].amount == 0

        """
        [Capture]
        - 1 payment_intent with status=canceled
        - 1 pgp_payment_intent with status=canceled
        """
        await self._capture_intents(
            cart_payment_processor=cart_payment_processor,
            cart_payment_repository=cart_payment_repository,
        )

        # Verify payment_intent status post capture
        post_cap_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        assert len(post_cap_payment_intents) == 1
        assert init_payment_intents[0].id == post_cap_payment_intents[0].id
        assert post_cap_payment_intents[0].status == IntentStatus.CANCELLED

        # Verify pgp_payment_intent status post capture
        post_cap_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            post_cap_payment_intents[0].id
        )
        assert len(post_cap_pgp_payment_intents) == 1
        assert init_pgp_payment_intents[0].id == post_cap_pgp_payment_intents[0].id
        assert post_cap_pgp_payment_intents[0].status == IntentStatus.CANCELLED

    async def _test_capture_after_cart_payment_creation_with_higher_adjustment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):

        cart_payment = await self._prepare_cart_payment(
            payer=payer,
            payment_method=payment_method,
            cart_payment_processor=cart_payment_processor,
        )

        """
        [Initial creation]
        - 1 payment_intent with status=require_capture
        - 1 pgp_payment_intent with status=require_capture
        """
        # Verify payment_intent status pre capture
        init_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        assert len(init_payment_intents) == 1
        assert init_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE

        # Verify pgp_payment_intent status pre capture
        init_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            init_payment_intents[0].id
        )
        assert len(init_pgp_payment_intents) == 1
        assert init_pgp_payment_intents[0].status == IntentStatus.REQUIRES_CAPTURE

        """
        [Adjustment - increase amount]
        - 2 payment_intents order by created at asc, with status=[canceled, require_capture]
        - 2 pgp_payment_intents order by created at asc, with status=[canceled, require_capture]
        - both new payment_intent and new pgp_payment_intent amount reflect updates
        """
        delta_amount = cart_payment.amount
        assert payer.id
        await self._update_cart_payment(
            cart_payment_processor=cart_payment_processor,
            existing_cart_payment=cart_payment,
            initial_payment_intent=init_payment_intents[0],
            idempotency_key=str(uuid4()),
            payer_id=payer.id,
            delta_amount=delta_amount,
        )

        post_adj_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        post_adj_payment_intents.sort(key=lambda pi: pi.created_at)
        assert len(post_adj_payment_intents) == 2
        assert post_adj_payment_intents[0].id == init_payment_intents[0].id
        assert post_adj_payment_intents[0].status == IntentStatus.CANCELLED
        assert post_adj_payment_intents[1].status == IntentStatus.REQUIRES_CAPTURE
        assert (
            post_adj_payment_intents[1].amount
            == init_pgp_payment_intents[0].amount + delta_amount
        )

        post_adj_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            post_adj_payment_intents[0].id
        ) + await cart_payment_repository.find_pgp_payment_intents(
            post_adj_payment_intents[1].id
        )

        assert len(post_adj_pgp_payment_intents) == 2
        assert post_adj_pgp_payment_intents[0].id == init_pgp_payment_intents[0].id
        assert post_adj_pgp_payment_intents[0].status == IntentStatus.CANCELLED
        assert post_adj_pgp_payment_intents[1].status == IntentStatus.REQUIRES_CAPTURE
        assert (
            post_adj_pgp_payment_intents[1].amount
            == init_pgp_payment_intents[0].amount + delta_amount
        )

        """
        [Capture]
        - 2 payment_intents order by created at asc, with status=[canceled, success]
        - 2 pgp_payment_intents order by created at asc, with status=[canceled, success]
        """
        await self._capture_intents(
            cart_payment_processor=cart_payment_processor,
            cart_payment_repository=cart_payment_repository,
        )

        # Verify payment_intent status post capture
        post_cap_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment.id
        )
        post_cap_payment_intents.sort(key=lambda pi: pi.created_at)
        assert len(post_cap_payment_intents) == 2
        assert init_payment_intents[0].id == post_cap_payment_intents[0].id
        assert post_cap_payment_intents[0].status == IntentStatus.CANCELLED
        assert post_cap_payment_intents[1].status == IntentStatus.SUCCEEDED

        # Verify pgp_payment_intent status post capture
        post_cap_pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
            post_cap_payment_intents[0].id
        ) + await cart_payment_repository.find_pgp_payment_intents(
            post_cap_payment_intents[1].id
        )

        assert len(post_cap_pgp_payment_intents) == 2
        assert init_pgp_payment_intents[0].id == post_cap_pgp_payment_intents[0].id
        assert post_cap_pgp_payment_intents[0].status == IntentStatus.CANCELLED
        assert post_cap_pgp_payment_intents[1].status == IntentStatus.SUCCEEDED

    async def _prepare_payer(self, payer_processor_v1: PayerProcessorV1) -> Payer:
        return await payer_processor_v1.create_payer(
            dd_payer_id="1",
            payer_type="store",
            email=f"{str(uuid4())}@doordash.com)",
            country=CountryCode.US,
            description="test-payer",
        )

    async def _prepare_payment_method(
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

    async def _capture_intents(
        self,
        cart_payment_repository: CartPaymentRepository,
        cart_payment_processor: CartPaymentProcessor,
    ):
        # todo: ideally should just use "capture_uncapture_payment_intents" here to run in job pool
        # though this could occasionally cause db transaction cannot be properly closed likely due to
        # some unknown race condition. need to investigate and revise.
        uncaptured_payment_intents = cart_payment_repository.find_payment_intents_that_require_capture_before_cutoff(
            datetime.utcnow()
        )

        async for payment_intent in uncaptured_payment_intents:
            await cart_payment_processor.capture_payment(payment_intent)

    @abstractmethod
    async def _prepare_cart_payment(
        self,
        payer: Payer,
        payment_method: PaymentMethod,
        cart_payment_processor: CartPaymentProcessor,
    ) -> CartPayment:
        pass

    @abstractmethod
    async def _update_cart_payment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        existing_cart_payment: CartPayment,
        initial_payment_intent: PaymentIntent,
        idempotency_key: str,
        payer_id: UUID,
        delta_amount: int,
    ):
        pass


@pytest.mark.external
@pytest.mark.asyncio
class TestCapturePaymentIntent(CapturePaymentIntentTestBase):
    @pytest.fixture(autouse=True)
    def enable_stripe_outbound(self, stripe_api: StripeAPISettings):
        stripe_api.enable_outbound()

    @pytest.fixture(autouse=True)
    def override_capture_delay(self, app_context: AppContext):
        original_capture_service_delay = (
            app_context.capture_service.default_capture_delay_in_minutes
        )
        app_context.capture_service.default_capture_delay_in_minutes = 0
        yield
        app_context.capture_service.default_capture_delay_in_minutes = (
            original_capture_service_delay
        )

    @pytest.fixture
    async def payer(self, payer_processor_v1: PayerProcessorV1) -> Payer:
        return await self._prepare_payer(payer_processor_v1)

    @pytest.fixture
    async def payment_method(
        self, payment_method_processor: PaymentMethodProcessor, payer: Payer
    ) -> PaymentMethod:
        return await self._prepare_payment_method(payment_method_processor, payer)

    async def test_capture_after_cart_payment_creation_without_adjustment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        return await super()._test_capture_after_cart_payment_creation_without_adjustment(
            cart_payment_processor, cart_payment_repository, payer, payment_method
        )

    async def test_capture_after_cart_payment_creation_with_partial_refund(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        return await super()._test_capture_after_cart_payment_creation_with_partial_refund(
            cart_payment_processor, cart_payment_repository, payer, payment_method
        )

    async def test_capture_after_cart_payment_creation_with_full_refund(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        return await super()._test_capture_after_cart_payment_creation_with_full_refund(
            cart_payment_processor, cart_payment_repository, payer, payment_method
        )

    async def test_capture_after_cart_payment_creation_with_higher_adjustment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        return await super()._test_capture_after_cart_payment_creation_with_higher_adjustment(
            cart_payment_processor, cart_payment_repository, payer, payment_method
        )

    async def _prepare_cart_payment(
        self,
        payer: Payer,
        payment_method: PaymentMethod,
        cart_payment_processor: CartPaymentProcessor,
    ) -> CartPayment:
        request = CartPayment(
            id=uuid4(),
            amount=1000,
            payer_id=payer.id,
            payment_method_id=payment_method.id,
            delay_capture=True,
            correlation_ids=CorrelationIds(reference_id="123", reference_type="3"),
            metadata={},
            client_description="client_description",
            payer_statement_description="description",
        )
        created = await cart_payment_processor.create_payment(
            request_cart_payment=request,
            idempotency_key=str(uuid4()),
            currency=Currency.USD,
            payment_country=CountryCode(payer.country),
        )
        return created

    async def _update_cart_payment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        existing_cart_payment: CartPayment,
        initial_payment_intent: PaymentIntent,
        idempotency_key: str,
        payer_id: UUID,
        delta_amount: int,
    ):

        await cart_payment_processor.update_payment(
            idempotency_key=idempotency_key,
            cart_payment_id=existing_cart_payment.id,
            payer_id=payer_id,
            amount=delta_amount + existing_cart_payment.amount,
            client_description="adjust cart payment description",
            split_payment=None,
        )


@pytest.mark.external
@pytest.mark.asyncio
class TestCapturePaymentIntentLegacy(CapturePaymentIntentTestBase):
    @pytest.fixture(autouse=True)
    def enable_stripe_outbound(self, stripe_api: StripeAPISettings):
        stripe_api.enable_outbound()

    @pytest.fixture(autouse=True)
    def override_capture_delay(self, app_context: AppContext):
        original_capture_service_delay = (
            app_context.capture_service.default_capture_delay_in_minutes
        )
        app_context.capture_service.default_capture_delay_in_minutes = 0
        yield
        app_context.capture_service.default_capture_delay_in_minutes = (
            original_capture_service_delay
        )

    @pytest.fixture
    async def payer(self, payer_processor_v1: PayerProcessorV1) -> Payer:
        return await self._prepare_payer(payer_processor_v1)

    @pytest.fixture
    async def payment_method(
        self, payment_method_processor: PaymentMethodProcessor, payer: Payer
    ) -> PaymentMethod:
        return await self._prepare_payment_method(payment_method_processor, payer)

    async def test_capture_after_cart_payment_creation_without_adjustment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        return await super()._test_capture_after_cart_payment_creation_without_adjustment(
            cart_payment_processor, cart_payment_repository, payer, payment_method
        )

    async def test_capture_after_cart_payment_creation_with_partial_refund(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        return await super()._test_capture_after_cart_payment_creation_with_partial_refund(
            cart_payment_processor, cart_payment_repository, payer, payment_method
        )

    async def test_capture_after_cart_payment_creation_with_full_refund(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        return await super()._test_capture_after_cart_payment_creation_with_full_refund(
            cart_payment_processor, cart_payment_repository, payer, payment_method
        )

    async def test_capture_after_cart_payment_creation_with_higher_adjustment(
        self,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        return await super()._test_capture_after_cart_payment_creation_with_higher_adjustment(
            cart_payment_processor, cart_payment_repository, payer, payment_method
        )

    async def _prepare_cart_payment(
        self,
        payer: Payer,
        payment_method: PaymentMethod,
        cart_payment_processor: CartPaymentProcessor,
    ) -> CartPayment:
        request = CartPayment(
            id=uuid4(),
            amount=1000,
            payer_id=payer.id,
            payment_method_id=payment_method.id,
            delay_capture=True,
            correlation_ids=CorrelationIds(reference_id="123", reference_type="3"),
            metadata={},
            client_description="client_description",
            payer_statement_description="description",
        )

        assert payer.payment_gateway_provider_customers

        created, _ = await cart_payment_processor.legacy_create_payment(
            request_cart_payment=request,
            idempotency_key=str(uuid4()),
            legacy_payment=LegacyPayment(
                dd_consumer_id=1,
                dd_country_id=None,
                dd_stripe_card_id=payment_method.dd_stripe_card_id,
                stripe_customer_id=payer.payment_gateway_provider_customers[
                    0
                ].payment_provider_customer_id,
                stripe_card_id="pm_card_mastercard",
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
        initial_payment_intent: PaymentIntent,
        idempotency_key: str,
        payer_id: UUID,
        delta_amount: int,
    ):

        await cart_payment_processor.update_payment_for_legacy_charge(
            idempotency_key=idempotency_key,
            dd_charge_id=initial_payment_intent.legacy_consumer_charge_id,
            amount=delta_amount,
            client_description="adjust cart payment description",
            dd_additional_payment_info=None,
            split_payment=None,
        )
