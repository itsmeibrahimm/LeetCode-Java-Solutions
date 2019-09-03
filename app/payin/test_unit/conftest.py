import pytest

from datetime import datetime
from typing import Optional, List
from unittest.mock import MagicMock
from uuid import UUID

from app.payin.core.cart_payment.processor import CartPaymentInterface
from app.payin.core.dispute.processor import DisputeProcessor, DisputeClient
from app.payin.tests.utils import FunctionMock, ContextMock
from app.payin.core.cart_payment.model import (
    CartPayment,
    CartMetadata,
    CartType,
    PaymentIntent,
    PgpPaymentIntent,
    PaymentCharge,
    PgpPaymentCharge,
    PaymentIntentAdjustmentHistory,
)
from app.payin.core.cart_payment.types import IntentStatus, ChargeStatus
from app.payin.tests import utils


class MockedPaymentRepo:
    async def insert_cart_payment(
        self,
        *,
        id: UUID,
        payer_id: str,
        type: str,
        client_description: Optional[str],
        reference_id: int,
        reference_ct_id: int,
        legacy_consumer_id: Optional[int],
        amount_original: int,
        amount_total: int,
        delay_capture: bool,
    ) -> CartPayment:
        return CartPayment(
            id=id,
            payer_id=payer_id,
            amount=amount_total,
            payment_method_id=None,  # Not populated until after intent pair is also created
            client_description=client_description,
            cart_metadata=CartMetadata(
                reference_id=reference_id,
                ct_reference_id=reference_ct_id,
                type=CartType(type),
            ),
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

    async def get_cart_payment_by_id(self, cart_payment_id: UUID) -> CartPayment:
        return utils.generate_cart_payment(id=cart_payment_id)

    async def insert_payment_intent(
        self,
        id: UUID,
        cart_payment_id: UUID,
        idempotency_key: str,
        amount_initiated: int,
        amount: int,
        application_fee_amount: Optional[int],
        country: str,
        currency: str,
        capture_method: str,
        confirmation_method: str,
        status: str,
        statement_descriptor: Optional[str],
        capture_after: Optional[datetime],
    ) -> PaymentIntent:
        return PaymentIntent(
            id=id,
            cart_payment_id=cart_payment_id,
            idempotency_key=idempotency_key,
            amount_initiated=amount_initiated,
            amount=amount,
            amount_capturable=None,
            amount_received=None,
            application_fee_amount=application_fee_amount,
            capture_method=capture_method,
            confirmation_method=confirmation_method,
            country=country,
            currency=currency,
            status=IntentStatus.INIT,
            statement_descriptor=statement_descriptor,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            captured_at=None,
            cancelled_at=None,
            capture_after=capture_after,
        )

    async def update_payment_intent_status(
        self, id: UUID, new_status: str, previous_status: str
    ) -> PaymentIntent:
        return utils.generate_payment_intent(id=id, status=new_status)

    async def update_payment_intent_amount(
        self, id: UUID, amount: int
    ) -> PaymentIntent:
        return utils.generate_payment_intent(id=id, amount=amount)

    async def get_payment_intents_for_cart_payment(
        self, cart_payment_id: UUID
    ) -> List[PaymentIntent]:
        return [utils.generate_payment_intent(cart_payment_id=cart_payment_id)]

    async def insert_pgp_payment_intent(
        self,
        id: UUID,
        payment_intent_id: UUID,
        idempotency_key: str,
        provider: str,
        payment_method_resource_id: str,
        currency: str,
        amount: int,
        application_fee_amount: Optional[int],
        payout_account_id: Optional[str],
        capture_method: str,
        confirmation_method: str,
        status: str,
        statement_descriptor: Optional[str],
    ) -> PgpPaymentIntent:
        return PgpPaymentIntent(
            id=id,
            payment_intent_id=payment_intent_id,
            idempotency_key=idempotency_key,
            provider=provider,
            resource_id=None,
            status=IntentStatus.INIT,
            invoice_resource_id=None,
            charge_resource_id=None,
            payment_method_resource_id=payment_method_resource_id,
            currency=currency,
            amount=amount,
            amount_capturable=None,
            amount_received=None,
            application_fee_amount=application_fee_amount,
            capture_method=capture_method,
            confirmation_method=confirmation_method,
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
        self, id: UUID, status: str, resource_id: str, charge_resource_id: str
    ) -> PgpPaymentIntent:
        return utils.generate_pgp_payment_intent(
            id=id,
            status=status,
            resource_id=resource_id,
            charge_resource_id=charge_resource_id,
        )

    async def find_pgp_payment_intents(
        self, payment_intent_id: UUID
    ) -> List[PgpPaymentIntent]:
        return [utils.generate_pgp_payment_intent(payment_intent_id=payment_intent_id)]

    async def insert_payment_charge(
        self,
        id: UUID,
        payment_intent_id: UUID,
        provider: str,
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
            provider=provider,
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
        provider: str,
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
            provider=provider,
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

    async def insert_payment_intent_adjustment_history(
        self,
        id: UUID,
        payer_id: str,
        payment_intent_id: UUID,
        amount: int,
        amount_original: int,
        amount_delta: int,
        currency: str,
    ) -> PaymentIntentAdjustmentHistory:
        return PaymentIntentAdjustmentHistory(
            id=id,
            payer_id=payer_id,
            payment_intent_id=payment_intent_id,
            amount=amount,
            amount_original=amount_original,
            amount_delta=amount_delta,
            currency=currency,
            created_at=datetime.now(),
        )


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
    payment_repo.update_payment_intent_status = mocked_repo.update_payment_intent_status
    payment_repo.update_payment_intent_amount = mocked_repo.update_payment_intent_amount
    payment_repo.get_payment_intents_for_cart_payment = (
        mocked_repo.get_payment_intents_for_cart_payment
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
    mocked_intent = MagicMock()
    mocked_intent.id = "test_intent_id"
    mocked_intent.status = "requires_capture"  # Assume delayed capture is used
    mocked_intent.charges = MagicMock()
    mocked_intent.charges.data = [MagicMock()]

    stripe.create_payment_intent = FunctionMock(return_value=mocked_intent)
    stripe.cancel_payment_intent = FunctionMock(return_value=mocked_intent)
    stripe.capture_payment_intent = FunctionMock(return_value=mocked_intent)

    # Refund functions
    mocked_refund = MagicMock()
    mocked_refund.id = "test_refund"
    mocked_refund.status = "succeeded"
    mocked_refund.amount = 200

    stripe.refund_charge = FunctionMock(return_value=mocked_refund)

    return stripe


@pytest.fixture
def cart_payment_interface(cart_payment_repo, stripe_interface):
    """
    Returns a cart payment interface with a default mocked stripe client and cart payment repository, where
    functions within these provide default (e.g. simple mock) responses.
    """
    cart_payment_interface = CartPaymentInterface(
        app_context=MagicMock(),
        req_context=MagicMock(),
        payment_repo=cart_payment_repo,
        payer_client=MagicMock(),
        payment_method_client=MagicMock(),
    )

    # Lookup functions
    cart_payment_interface._get_required_payment_resource_ids = FunctionMock(
        return_value=("payment_method_id", "customer_id")
    )

    # Stripe functions
    cart_payment_interface.app_context.stripe = stripe_interface

    return cart_payment_interface


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
