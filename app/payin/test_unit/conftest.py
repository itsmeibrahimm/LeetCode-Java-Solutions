from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from asynctest import create_autospec

from app.commons.types import PgpCode, CountryCode, Currency
from app.payin.capture.service import CaptureService
from app.payin.core.cart_payment.model import (
    CartPayment,
    CorrelationIds,
    PaymentIntent,
    PgpPaymentIntent,
    PaymentCharge,
    PgpPaymentCharge,
    PaymentIntentAdjustmentHistory,
    LegacyConsumerCharge,
    LegacyStripeCharge,
    LegacyPayment,
    Refund,
    PgpRefund,
)
from app.payin.core.cart_payment.processor import (
    CartPaymentInterface,
    LegacyPaymentInterface,
    CartPaymentProcessor,
)
from app.payin.core.cart_payment.types import (
    IntentStatus,
    ChargeStatus,
    LegacyConsumerChargeId,
    LegacyStripeChargeStatus,
    RefundStatus,
)
from app.payin.core.dispute.processor import DisputeProcessor, DisputeClient
from app.payin.core.payer.model import RawPayer
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.types import PgpPaymentMethod
from app.payin.core.types import PgpPaymentMethodResourceId, PgpPayerResourceId
from app.payin.repository.cart_payment_repo import (
    UpdatePgpPaymentIntentWhereInput,
    UpdatePgpPaymentIntentSetInput,
    UpdateCartPaymentPostCancellationInput,
)
from app.payin.tests import utils
from app.payin.tests.utils import FunctionMock, ContextMock, generate_payer


class MockedPaymentRepo:
    async def insert_cart_payment(
        self,
        *,
        id: UUID,
        payer_id: str,
        client_description: Optional[str],
        reference_id: str,
        reference_type: str,
        legacy_consumer_id: Optional[int],
        amount_original: int,
        amount_total: int,
        delay_capture: bool,
        metadata: Dict[str, Any],
        legacy_stripe_card_id: int,
        legacy_provider_customer_id: str,
        legacy_provider_card_id: str,
    ) -> CartPayment:
        return CartPayment(
            id=id,
            payer_id=payer_id,
            amount=amount_total,
            payment_method_id=None,  # Not populated until after intent pair is also created
            client_description=client_description,
            correlation_ids=CorrelationIds(
                reference_id=reference_id, reference_type=reference_type
            ),
            metadata=metadata,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            delay_capture=delay_capture,
        )

    async def update_cart_payment_details(
        self, cart_payment_id: UUID, amount: int, client_description: Optional[str]
    ) -> CartPayment:
        cart_payment = utils.generate_cart_payment()
        cart_payment.id = cart_payment_id
        cart_payment.amount = amount
        cart_payment.client_description = client_description
        return cart_payment

    async def update_cart_payment_post_cancellation(
        self,
        update_cart_payment_post_cancellation_input: UpdateCartPaymentPostCancellationInput,
    ) -> CartPayment:
        cart_payment = utils.generate_cart_payment()
        cart_payment.id = update_cart_payment_post_cancellation_input.id
        cart_payment.updated_at = update_cart_payment_post_cancellation_input.updated_at
        cart_payment.deleted_at = update_cart_payment_post_cancellation_input.deleted_at
        return cart_payment

    async def get_cart_payment_by_id(
        self, cart_payment_id: UUID
    ) -> Tuple[Optional[CartPayment], Optional[LegacyPayment]]:
        return (
            utils.generate_cart_payment(id=cart_payment_id),
            utils.generate_legacy_payment(),
        )

    async def insert_payment_intent(
        self,
        id: UUID,
        cart_payment_id: UUID,
        idempotency_key: str,
        amount_initiated: int,
        amount: int,
        application_fee_amount: Optional[int],
        country: CountryCode,
        currency: str,
        capture_method: str,
        status: str,
        statement_descriptor: Optional[str],
        capture_after: Optional[datetime],
        payment_method_id: Optional[str],
        metadata: Optional[Dict[str, Any]],
        legacy_consumer_charge_id: Optional[LegacyConsumerChargeId],
    ) -> PaymentIntent:
        return PaymentIntent(
            id=id,
            cart_payment_id=cart_payment_id,
            idempotency_key=idempotency_key,
            amount_initiated=amount_initiated,
            amount=amount,
            application_fee_amount=application_fee_amount,
            capture_method=capture_method,
            country=country,
            currency=currency,
            status=IntentStatus.INIT,
            statement_descriptor=statement_descriptor,
            payment_method_id=payment_method_id,
            metadata=metadata,
            legacy_consumer_charge_id=legacy_consumer_charge_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            captured_at=None,
            cancelled_at=None,
            capture_after=capture_after,
        )

    async def update_payment_intent_capture_state(
        self, id: UUID, status: str, captured_at: datetime
    ):
        return utils.generate_payment_intent(
            id=id, status=status, captured_at=captured_at
        )

    async def update_payment_intent_status(
        self,
        update_payment_intent_status_where_input,
        update_payment_intent_status_set_input,
    ) -> PaymentIntent:
        return utils.generate_payment_intent(
            id=update_payment_intent_status_where_input.id,
            status=update_payment_intent_status_set_input.status,
        )

    async def update_payment_intent_amount(
        self, id: UUID, amount: int
    ) -> PaymentIntent:
        return utils.generate_payment_intent(id=id, amount=amount)

    async def get_payment_intents_for_cart_payment(
        self, cart_payment_id: UUID
    ) -> List[PaymentIntent]:
        return [utils.generate_payment_intent(cart_payment_id=cart_payment_id)]

    async def get_payment_intent_for_legacy_consumer_charge_id(
        self, charge_id: int
    ) -> Optional[PaymentIntent]:
        return utils.generate_payment_intent()

    async def insert_pgp_payment_intent(
        self,
        id: UUID,
        payment_intent_id: UUID,
        idempotency_key: str,
        pgp_code: PgpCode,
        payment_method_resource_id: str,
        customer_resource_id: str,
        currency: str,
        amount: int,
        application_fee_amount: Optional[int],
        payout_account_id: Optional[str],
        capture_method: str,
        status: str,
        statement_descriptor: Optional[str],
    ) -> PgpPaymentIntent:
        return PgpPaymentIntent(
            id=id,
            payment_intent_id=payment_intent_id,
            idempotency_key=idempotency_key,
            pgp_code=pgp_code,
            resource_id=None,
            status=IntentStatus.INIT,
            invoice_resource_id=None,
            charge_resource_id=None,
            payment_method_resource_id=payment_method_resource_id,
            customer_resource_id=customer_resource_id,
            currency=currency,
            amount=amount,
            amount_capturable=None,
            amount_received=None,
            application_fee_amount=application_fee_amount,
            capture_method=capture_method,
            payout_account_id=payout_account_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            captured_at=None,
            cancelled_at=None,
        )

    async def update_pgp_payment_intent_status(
        self, id: UUID, status: str
    ) -> PgpPaymentIntent:
        return utils.generate_pgp_payment_intent(id=id, status=status)

    async def update_pgp_payment_intent_amount(
        self, id: UUID, amount: int
    ) -> PgpPaymentIntent:
        return utils.generate_pgp_payment_intent(id=id, amount=amount)

    async def update_pgp_payment_intent(
        self,
        update_pgp_payment_intent_where_input: UpdatePgpPaymentIntentWhereInput,
        update_pgp_payment_intent_set_input: UpdatePgpPaymentIntentSetInput,
    ) -> PgpPaymentIntent:
        return utils.generate_pgp_payment_intent(
            id=update_pgp_payment_intent_where_input.id,
            status=update_pgp_payment_intent_set_input.status,
            resource_id=update_pgp_payment_intent_set_input.resource_id,
            charge_resource_id=update_pgp_payment_intent_set_input.charge_resource_id,
            amount_capturable=update_pgp_payment_intent_set_input.amount_capturable,
            amount_received=update_pgp_payment_intent_set_input.amount_received,
        )

    async def find_pgp_payment_intents(
        self, payment_intent_id: UUID
    ) -> List[PgpPaymentIntent]:
        return [utils.generate_pgp_payment_intent(payment_intent_id=payment_intent_id)]

    async def insert_payment_charge(
        self,
        id: UUID,
        payment_intent_id: UUID,
        pgp_code: PgpCode,
        idempotency_key: str,
        status: str,
        currency: str,
        amount: int,
        amount_refunded: int,
        application_fee_amount: Optional[int],
        payout_account_id: Optional[str],
    ) -> PaymentCharge:
        return PaymentCharge(
            id=id,
            payment_intent_id=payment_intent_id,
            pgp_code=pgp_code,
            idempotency_key=idempotency_key,
            status=ChargeStatus(status),
            currency=currency,
            amount=amount,
            amount_refunded=amount_refunded,
            application_fee_amount=application_fee_amount,
            payout_account_id=payout_account_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            captured_at=None,
            cancelled_at=None,
        )

    async def insert_pgp_payment_charge(
        self,
        id: UUID,
        payment_charge_id: UUID,
        pgp_code: PgpCode,
        idempotency_key: str,
        status: str,
        currency: str,
        amount: int,
        amount_refunded: int,
        application_fee_amount: Optional[int],
        payout_account_id: Optional[str],
        resource_id: Optional[str],
        intent_resource_id: Optional[str],
        invoice_resource_id: Optional[str],
        payment_method_resource_id: Optional[str],
    ) -> PgpPaymentCharge:
        return PgpPaymentCharge(
            id=id,
            payment_charge_id=payment_charge_id,
            pgp_code=pgp_code,
            idempotency_key=idempotency_key,
            status=ChargeStatus(status),
            currency=currency,
            amount=amount,
            amount_refunded=amount_refunded,
            application_fee_amount=application_fee_amount,
            payout_account_id=payout_account_id,
            resource_id=resource_id,
            intent_resource_id=intent_resource_id,
            invoice_resource_id=invoice_resource_id,
            payment_method_resource_id=payment_method_resource_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            captured_at=None,
            cancelled_at=None,
        )

    async def update_payment_charge_status(
        self, payment_intent_id: UUID, status: str
    ) -> PaymentCharge:
        return utils.generate_payment_charge(
            payment_intent_id=payment_intent_id, status=ChargeStatus(status)
        )

    async def update_payment_charge(
        self, payment_intent_id: UUID, status: str, amount_refunded: int
    ) -> PaymentCharge:
        return utils.generate_payment_charge(
            payment_intent_id=payment_intent_id,
            status=ChargeStatus(status),
            amount_refunded=amount_refunded,
        )

    async def update_payment_charge_amount(
        self, payment_intent_id: UUID, amount: int
    ) -> PaymentCharge:
        return utils.generate_payment_charge(
            payment_intent_id=payment_intent_id, amount=amount
        )

    async def update_pgp_payment_charge(
        self, payment_charge_id: UUID, status: str, amount: int, amount_refunded: int
    ) -> PgpPaymentCharge:
        return utils.generate_pgp_payment_charge(
            payment_charge_id=payment_charge_id,
            status=ChargeStatus(status),
            amount=amount,
            amount_refunded=amount_refunded,
        )

    async def update_pgp_payment_charge_status(
        self, payment_charge_id: UUID, status: str
    ) -> PgpPaymentCharge:
        return utils.generate_pgp_payment_charge(
            payment_charge_id=payment_charge_id, status=ChargeStatus(status)
        )

    async def update_pgp_payment_charge_amount(
        self, payment_charge_id: UUID, amount: int
    ) -> PgpPaymentCharge:
        return utils.generate_pgp_payment_charge(
            payment_charge_id=payment_charge_id, amount=amount
        )

    async def get_intent_pair_by_provider_charge_id(
        self, provider_charge_id: str
    ) -> Tuple[Optional[PaymentIntent], Optional[PgpPaymentIntent]]:
        return utils.generate_payment_intent(), utils.generate_pgp_payment_intent()

    async def insert_payment_intent_adjustment_history(
        self,
        id: UUID,
        payer_id: UUID,
        payment_intent_id: UUID,
        amount: int,
        amount_original: int,
        amount_delta: int,
        currency: str,
        idempotency_key: str,
    ) -> PaymentIntentAdjustmentHistory:
        return PaymentIntentAdjustmentHistory(
            id=id,
            payer_id=payer_id,
            payment_intent_id=payment_intent_id,
            amount=amount,
            amount_original=amount_original,
            amount_delta=amount_delta,
            currency=currency,
            idempotency_key=idempotency_key,
            created_at=datetime.now(),
        )

    async def insert_legacy_consumer_charge(
        self,
        target_ct_id: int,
        target_id: int,
        consumer_id: int,
        idempotency_key: str,
        is_stripe_connect_based: bool,
        country_id: int,
        currency: Currency,
        stripe_customer_id: Optional[int],
        total: int,
        original_total: int,
    ) -> LegacyConsumerCharge:
        return LegacyConsumerCharge(
            id=LegacyConsumerChargeId(1),
            target_id=target_id,
            target_ct_id=target_ct_id,
            idempotency_key=idempotency_key,
            is_stripe_connect_based=is_stripe_connect_based,
            total=total,
            original_total=original_total,
            currency=currency,
            country_id=country_id,
            issue_id=None,
            stripe_customer_id=stripe_customer_id,
            created_at=datetime.now(),
        )

    async def get_legacy_consumer_charge_by_id(
        self, id: int
    ) -> Optional[LegacyConsumerCharge]:
        return utils.generate_legacy_consumer_charge()

    async def insert_legacy_stripe_charge(
        self,
        stripe_id: str,
        card_id: Optional[int],
        charge_id: int,
        amount: int,
        amount_refunded: int,
        currency: Currency,
        status: LegacyStripeChargeStatus,
        idempotency_key: str,
        additional_payment_info: Optional[str],
        description: Optional[str],
        error_reason: Optional[str],
    ) -> LegacyStripeCharge:
        return LegacyStripeCharge(
            id=1,
            amount=amount,
            amount_refunded=amount_refunded,
            currency=currency,
            status=status,
            error_reason=error_reason,
            additional_payment_info=additional_payment_info,
            description=description,
            idempotency_key=idempotency_key,
            card_id=card_id,
            charge_id=charge_id,
            stripe_id=stripe_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            refunded_at=None,
        )

    async def update_legacy_stripe_charge_add_to_amount_refunded(
        self, stripe_id: str, additional_amount_refunded: int, refunded_at: datetime
    ):
        return utils.generate_legacy_stripe_charge(
            stripe_id=stripe_id,
            amount_refunded=additional_amount_refunded,
            refunded_at=refunded_at,
        )

    async def update_legacy_stripe_charge_refund(
        self, stripe_id: str, amount_refunded: int, refunded_at: datetime
    ):
        return utils.generate_legacy_stripe_charge(
            stripe_id=stripe_id,
            amount_refunded=amount_refunded,
            refunded_at=refunded_at,
        )

    async def update_legacy_stripe_charge_provider_details(
        self,
        id: int,
        stripe_id: str,
        amount: int,
        amount_refunded: int,
        status: LegacyStripeChargeStatus,
    ):
        return utils.generate_legacy_stripe_charge(
            stripe_id=stripe_id,
            amount=amount,
            amount_refunded=amount_refunded,
            status=status,
        )

    async def update_legacy_stripe_charge_error_details(
        self,
        id: int,
        stripe_id: str,
        status: LegacyStripeChargeStatus,
        error_reason: str,
    ):
        return utils.generate_legacy_stripe_charge(
            stripe_id=stripe_id, status=status, error_reason=error_reason
        )

    async def update_legacy_stripe_charge_status(
        self, stripe_charge_id: str, status: LegacyStripeChargeStatus
    ):
        return utils.generate_legacy_stripe_charge(
            stripe_id=stripe_charge_id, status=status
        )

    async def get_legacy_stripe_charge_by_stripe_id(
        self, stripe_charge_id: str
    ) -> Optional[LegacyStripeCharge]:
        return utils.generate_legacy_stripe_charge(stripe_id=stripe_charge_id)

    async def get_legacy_stripe_charges_by_charge_id(
        self, charge_id: int
    ) -> List[LegacyStripeCharge]:
        return [utils.generate_legacy_stripe_charge()]

    async def get_payment_intent_adjustment_history(
        self, payment_intent_id: UUID, idempotency_key: str
    ) -> Optional[PaymentIntentAdjustmentHistory]:
        return None

    async def get_refund_by_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[Refund]:
        return None

    async def insert_refund(
        self,
        id: UUID,
        payment_intent_id: UUID,
        idempotency_key: str,
        status: RefundStatus,
        amount: int,
        reason: Optional[str],
    ) -> Refund:
        return Refund(
            id=id,
            payment_intent_id=payment_intent_id,
            idempotency_key=idempotency_key,
            status=status,
            amount=amount,
            reason=reason,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    async def insert_pgp_refund(
        self,
        id: UUID,
        refund_id: UUID,
        idempotency_key: str,
        status: RefundStatus,
        pgp_code: PgpCode,
        amount: int,
        reason: Optional[str],
    ) -> PgpRefund:
        return PgpRefund(
            id=id,
            refund_id=refund_id,
            idempotency_key=idempotency_key,
            status=status,
            amount=amount,
            reason=reason,
            pgp_code=pgp_code,
            pgp_resource_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    async def get_pgp_refund_by_refund_id(self, refund_id: UUID) -> Optional[PgpRefund]:
        return None

    async def update_refund_status(
        self, refund_id: UUID, status: RefundStatus
    ) -> Refund:
        return utils.generate_refund(status=status)

    async def update_pgp_refund(
        self, pgp_refund_id: UUID, status: RefundStatus, pgp_resource_id: str
    ) -> PgpRefund:
        return utils.generate_pgp_refund(status=status, pgp_resource_id=pgp_resource_id)


@pytest.fixture
def cart_payment_repo():
    """
    Provide a mocked cart_payment repository class.  Functions simply return MagicMocks.
    Tests that require specific behaviors can update mocked functions as needed.

    Returns:
        MagicMock -- Mocked cart payment repo.
    """
    payment_repo = MagicMock()
    mocked_repo = MockedPaymentRepo()

    # Cart Payment DB Functions
    payment_repo.insert_cart_payment = mocked_repo.insert_cart_payment
    payment_repo.update_cart_payment_details = mocked_repo.update_cart_payment_details
    payment_repo.get_cart_payment_by_id = mocked_repo.get_cart_payment_by_id

    # Intent DB Functions
    payment_repo.insert_payment_intent = mocked_repo.insert_payment_intent
    payment_repo.update_payment_intent_capture_state = (
        mocked_repo.update_payment_intent_capture_state
    )
    payment_repo.update_payment_intent_status = mocked_repo.update_payment_intent_status
    payment_repo.update_payment_intent_amount = mocked_repo.update_payment_intent_amount
    payment_repo.get_payment_intents_for_cart_payment = (
        mocked_repo.get_payment_intents_for_cart_payment
    )
    payment_repo.get_payment_intent_for_legacy_consumer_charge_id = (
        mocked_repo.get_payment_intent_for_legacy_consumer_charge_id
    )
    payment_repo.update_payment_intent_capture_state = (
        mocked_repo.update_payment_intent_capture_state
    )

    # Pgp Intent DB Functions
    payment_repo.insert_pgp_payment_intent = mocked_repo.insert_pgp_payment_intent
    payment_repo.update_pgp_payment_intent = mocked_repo.update_pgp_payment_intent
    payment_repo.update_pgp_payment_intent_status = (
        mocked_repo.update_pgp_payment_intent_status
    )
    payment_repo.update_pgp_payment_intent_amount = (
        mocked_repo.update_pgp_payment_intent_amount
    )
    payment_repo.find_pgp_payment_intents = mocked_repo.find_pgp_payment_intents
    payment_repo.get_payment_intent_for_idempotency_key = FunctionMock(
        return_value=None
    )
    payment_repo.get_intent_pair_by_provider_charge_id = (
        mocked_repo.get_intent_pair_by_provider_charge_id
    )

    # Intent history table
    payment_repo.insert_payment_intent_adjustment_history = (
        mocked_repo.insert_payment_intent_adjustment_history
    )

    # Charge DB Functions
    payment_repo.insert_payment_charge = mocked_repo.insert_payment_charge
    payment_repo.update_payment_charge = mocked_repo.update_payment_charge
    payment_repo.update_payment_charge_amount = mocked_repo.update_payment_charge_amount
    payment_repo.update_payment_charge_status = mocked_repo.update_payment_charge_status

    # Pgp Charge DB Functions
    payment_repo.insert_pgp_payment_charge = mocked_repo.insert_pgp_payment_charge
    payment_repo.update_pgp_payment_charge = mocked_repo.update_pgp_payment_charge
    payment_repo.update_pgp_payment_charge_amount = (
        mocked_repo.update_pgp_payment_charge_amount
    )
    payment_repo.update_pgp_payment_charge_status = (
        mocked_repo.update_pgp_payment_charge_status
    )

    # Legacy charges
    payment_repo.insert_legacy_consumer_charge = (
        mocked_repo.insert_legacy_consumer_charge
    )
    payment_repo.get_legacy_consumer_charge_by_id = (
        mocked_repo.get_legacy_consumer_charge_by_id
    )
    payment_repo.insert_legacy_stripe_charge = mocked_repo.insert_legacy_stripe_charge
    payment_repo.update_legacy_stripe_charge_add_to_amount_refunded = (
        mocked_repo.update_legacy_stripe_charge_add_to_amount_refunded
    )
    payment_repo.update_legacy_stripe_charge_refund = (
        mocked_repo.update_legacy_stripe_charge_refund
    )
    payment_repo.update_legacy_stripe_charge_provider_details = (
        mocked_repo.update_legacy_stripe_charge_provider_details
    )
    payment_repo.update_legacy_stripe_charge_error_details = (
        mocked_repo.update_legacy_stripe_charge_error_details
    )
    payment_repo.update_legacy_stripe_charge_status = (
        mocked_repo.update_legacy_stripe_charge_status
    )
    payment_repo.get_legacy_stripe_charge_by_stripe_id = (
        mocked_repo.get_legacy_stripe_charge_by_stripe_id
    )
    payment_repo.get_legacy_stripe_charges_by_charge_id = (
        mocked_repo.get_legacy_stripe_charges_by_charge_id
    )

    # Refunds
    payment_repo.insert_refund = mocked_repo.insert_refund
    payment_repo.get_payment_intent_adjustment_history = (
        mocked_repo.get_payment_intent_adjustment_history
    )
    payment_repo.get_refund_by_idempotency_key = (
        mocked_repo.get_refund_by_idempotency_key
    )
    payment_repo.update_refund_status = mocked_repo.update_refund_status

    payment_repo.insert_pgp_refund = mocked_repo.insert_pgp_refund
    payment_repo.get_pgp_refund_by_refund_id = mocked_repo.get_pgp_refund_by_refund_id
    payment_repo.update_pgp_refund = mocked_repo.update_pgp_refund

    payment_repo.update_cart_payment_post_cancellation = (
        mocked_repo.update_cart_payment_post_cancellation
    )

    # Transaction function
    payment_repo.payment_database_transaction = ContextMock()

    return payment_repo


@pytest.fixture
def stripe_interface():
    """
    Provide a mocked stripe interface.  Functions return a dummy objects, such as a mocked
    PaymentIntent isntance.

    Returns:
        MagicMock -- Stripe instance.
    """
    stripe = MagicMock()

    # Intent functions

    stripe.create_payment_intent = FunctionMock(
        return_value=utils.generate_provider_intent()
    )
    stripe.cancel_payment_intent = FunctionMock(
        return_value=utils.generate_provider_intent(amount_refunded=500)
    )

    async def mocked_capture(*args, **kwargs):
        capture_request = kwargs["request"]
        captured_provider_intent = utils.generate_provider_intent()
        captured_provider_intent.amount_received = capture_request.amount_to_capture
        return captured_provider_intent

    stripe.capture_payment_intent = mocked_capture

    # Refund functions
    mocked_refund = MagicMock()
    mocked_refund.id = "test_refund"
    mocked_refund.status = "succeeded"
    mocked_refund.amount = 200
    mocked_refund.charge = "ch_AUgV0YDud8EOlo"

    stripe.refund_charge = FunctionMock(return_value=mocked_refund)

    return stripe


@pytest.fixture
def cart_payment_interface(cart_payment_repo, stripe_interface):
    """
    Returns a cart payment interface with a default mocked stripe client and cart payment repository, where
    functions within these provide default (e.g. simple mock) responses.
    """
    app_context = MagicMock()
    app_context.capture_service = CaptureService(default_capture_delay_in_minutes=2)
    cart_payment_interface = CartPaymentInterface(
        app_context=app_context,
        req_context=MagicMock(),
        payment_repo=cart_payment_repo,
        payer_client=create_autospec(PayerClient),
        payment_method_client=MagicMock(),
        stripe_async_client=stripe_interface,
    )

    # Lookup functions
    cart_payment_interface.get_pgp_payment_method_by_legacy_payment = FunctionMock(
        return_value=(
            PgpPaymentMethod(
                pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                    "payment_method_ref_id"
                ),
                pgp_payer_resource_id=PgpPayerResourceId("customer_id"),
            ),
            utils.generate_legacy_payment(),
        )
    )
    cart_payment_interface.get_pgp_payment_method = FunctionMock(
        return_value=(
            PgpPaymentMethod(
                pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                    "payment_method_ref_id"
                ),
                pgp_payer_resource_id=PgpPayerResourceId("customer_id"),
            ),
            utils.generate_legacy_payment(),
        )
    )

    # Stripe functions
    cart_payment_interface.app_context.stripe = stripe_interface

    cart_payment_interface.log = MagicMock()

    return cart_payment_interface


@pytest.fixture
def legacy_payment_interface(cart_payment_repo):
    return LegacyPaymentInterface(
        app_context=MagicMock(),
        req_context=MagicMock(),
        payment_repo=cart_payment_repo,
        stripe_async_client=MagicMock(),
    )


@pytest.fixture
def cart_payment_processor(
    cart_payment_interface: CartPaymentInterface,
    legacy_payment_interface: LegacyPaymentInterface,
):
    cart_payment_processor = CartPaymentProcessor(
        log=MagicMock(),
        cart_payment_interface=cart_payment_interface,
        legacy_payment_interface=legacy_payment_interface,
    )
    raw_payer_mock = create_autospec(RawPayer)
    raw_payer_mock.to_payer.return_value = generate_payer()
    cart_payment_processor.cart_payment_interface.payer_client.get_raw_payer.return_value = (  # type: ignore
        raw_payer_mock
    )
    return cart_payment_processor


@pytest.fixture
def dispute_repo():
    dispute_repo = MagicMock()
    dispute_repo.get_dispute_by_dispute_id = FunctionMock(return_value=MagicMock())
    dispute_repo.main_database_transaction = ContextMock()
    return dispute_repo


@pytest.fixture
def dispute_processor():
    dispute_processor = DisputeProcessor(dispute_client=MagicMock(), log=MagicMock())
    return dispute_processor


@pytest.fixture
def dispute_client():
    dispute_client = DisputeClient(
        app_ctxt=MagicMock(), log=MagicMock(), dispute_repo=dispute_repo
    )
    return dispute_client
