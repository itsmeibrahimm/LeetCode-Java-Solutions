from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

import pytest

from app.commons.context.app_context import AppContext
from app.commons.types import CountryCode, Currency, PgpCode
from app.conftest import StripeAPISettings
from app.payin.core.cart_payment.model import (
    CartPayment,
    CorrelationIds,
    LegacyPayment,
    PaymentIntent,
    PgpPaymentIntent,
)
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.types import IntentStatus, LegacyStripeChargeStatus
from app.payin.core.payer.model import Payer
from app.payin.core.payer.v1.processor import PayerProcessorV1
from app.payin.core.payment_method.model import PaymentMethod
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.payment_method.types import LegacyPaymentMethodInfo
from app.payin.repository.cart_payment_repo import CartPaymentRepository


@dataclass
class PgpPaymentIntentState:
    status: IntentStatus
    amnt: int


@dataclass
class StripeChargeState:
    status: LegacyStripeChargeStatus
    amnt: int
    amnt_refunded: int


@dataclass
class PaymentIntentState:
    status: IntentStatus
    amnt: int
    pgp_payment_intent_state: PgpPaymentIntentState
    stripe_charge_state: StripeChargeState


@dataclass
class CartPaymentState:
    description: str
    initial_amount: int
    amnt_delta_update: Optional[int]
    expected_amount: int
    capture_intents: bool
    payment_intent_states: List[PaymentIntentState]

    def __post_init__(self):
        if self.amnt_delta_update and self.capture_intents:
            raise ValueError(
                "only 1 of capture_intents and amnt_delta_update can be specified in a single state change"
            )


create_no_adjust_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.SUCCEEDED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.SUCCEEDED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
]
create_and_partial_refund_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="[partial refund] adjust cart payment with -500 amount",
        initial_amount=1000,
        amnt_delta_update=-500,
        expected_amount=500,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=500,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=500, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=500,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=500,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=500,
                status=IntentStatus.SUCCEEDED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=500, status=IntentStatus.SUCCEEDED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=500,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
]

create_and_full_refund_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="[full refund] adjust cart payment with -1000 amount",
        initial_amount=1000,
        amnt_delta_update=-1000,
        expected_amount=0,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=0,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=0, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=0,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=0,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=0, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
]

create_and_partial_refund_and_full_refund_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="[partial refund] adjust cart payment with -200 amount",
        initial_amount=1000,
        amnt_delta_update=-200,
        expected_amount=800,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=800,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=800, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=200,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="[full refund] adjust cart payment with -800 amount",
        initial_amount=1000,
        amnt_delta_update=-800,
        expected_amount=0,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=0,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=0, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=0,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=0,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=0, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
]

create_and_partial_refund_and_adjust_to_no_exceed_original_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="[partial refund] adjust cart payment with -200 amount",
        initial_amount=1000,
        amnt_delta_update=-200,
        expected_amount=800,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=800,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=800, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=200,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="adjust cart payment with +50 amount",
        initial_amount=1000,
        amnt_delta_update=50,
        expected_amount=850,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=850,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=850, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=150,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=850,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=850,
                status=IntentStatus.SUCCEEDED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=850, status=IntentStatus.SUCCEEDED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=150,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
]

create_and_partial_refund_and_adjust_to_exceed_original_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="[partial refund] cart payment with -200 amount",
        initial_amount=1000,
        amnt_delta_update=-200,
        expected_amount=800,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=800,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=800, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=200,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="adjust cart payment with +300 amount",
        initial_amount=1000,
        amnt_delta_update=300,
        expected_amount=1100,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=800,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=800, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=1100,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1100, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1100,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1100,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=800,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=800, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=1100,
                status=IntentStatus.SUCCEEDED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1100, status=IntentStatus.SUCCEEDED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1100,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
]

create_and_adjust_to_exceed_original_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="adjust cart payment with +300 amount",
        initial_amount=1000,
        amnt_delta_update=300,
        expected_amount=1300,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=1300,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1300, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1300,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1300,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=1300,
                status=IntentStatus.SUCCEEDED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1300, status=IntentStatus.SUCCEEDED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1300,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
]

create_and_adjust_to_exceed_original_and_full_refund_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="adjust cart payment with +300 amount",
        initial_amount=1000,
        amnt_delta_update=300,
        expected_amount=1300,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=1300,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1300, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1300,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
    CartPaymentState(
        description="[full refund] cart payment with -1300 amount",
        initial_amount=1000,
        amnt_delta_update=-1300,
        expected_amount=0,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=0,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=0, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1300,
                    amnt_refunded=1300,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=0,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=0,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=0, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1300,
                    amnt_refunded=1300,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
]

create_and_adjust_to_exceed_original_and_partial_refund_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="adjust cart payment with +300 amount",
        initial_amount=1000,
        amnt_delta_update=300,
        expected_amount=1300,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=1300,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1300, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1300,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
    CartPaymentState(
        description="adjust cart payment with -300 amount",
        initial_amount=1000,
        amnt_delta_update=-300,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1300,
                    amnt_refunded=300,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.CANCELLED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.CANCELLED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=1000,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.SUCCEEDED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.SUCCEEDED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1300,
                    amnt_refunded=300,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            ),
        ],
    ),
]

create_and_partial_refund_and_partial_refund_test_data = [
    CartPaymentState(
        description="create cart payment with 1000 amount",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=1000,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=1000,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=1000, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=0,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="[partial refund] adjust cart payment with -200 amount",
        initial_amount=1000,
        amnt_delta_update=-200,
        expected_amount=800,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=800,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=800, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=200,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="[partial refund] cart payment with -200 amount",
        initial_amount=1000,
        amnt_delta_update=-200,
        expected_amount=600,
        capture_intents=False,
        payment_intent_states=[
            PaymentIntentState(
                amnt=600,
                status=IntentStatus.REQUIRES_CAPTURE,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=600, status=IntentStatus.REQUIRES_CAPTURE
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=400,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
    CartPaymentState(
        description="capture cart payment",
        initial_amount=1000,
        amnt_delta_update=None,
        expected_amount=600,
        capture_intents=True,
        payment_intent_states=[
            PaymentIntentState(
                amnt=600,
                status=IntentStatus.SUCCEEDED,
                pgp_payment_intent_state=PgpPaymentIntentState(
                    amnt=600, status=IntentStatus.SUCCEEDED
                ),
                stripe_charge_state=StripeChargeState(
                    amnt=1000,
                    amnt_refunded=400,
                    status=LegacyStripeChargeStatus.SUCCEEDED,
                ),
            )
        ],
    ),
]

cart_payment_delay_capture_state_transit_tests = [
    pytest.param(create_no_adjust_test_data, id="create_no_adjust"),
    pytest.param(create_and_partial_refund_test_data, id="create_and_partial_refund"),
    pytest.param(create_and_full_refund_test_data, id="create_and_full_refund"),
    pytest.param(
        create_and_partial_refund_and_full_refund_test_data,
        id="create_and_partial_refund_and_full_refund",
    ),
    pytest.param(
        create_and_partial_refund_and_partial_refund_test_data,
        id="create_and_partial_refund_and_partial_refund_test_data",
    ),
    # ignore this for now, when determine higher amount adjust, we only look at cartpayment amount
    # but not captureable amount for simplification
    # pytest.param(create_and_partial_refund_and_adjust_to_no_exceed_original_test_data,
    #              id="create_and_partial_refund_and_adjust_to_no_exceed_original"),
    pytest.param(
        create_and_partial_refund_and_adjust_to_exceed_original_test_data,
        id="create_and_partial_refund_and_adjust_to_exceed_original",
    ),
    pytest.param(
        create_and_adjust_to_exceed_original_test_data,
        id="create_and_adjust_to_exceed_original",
    ),
    pytest.param(
        create_and_adjust_to_exceed_original_and_partial_refund_test_data,
        id="create_and_adjust_to_exceed_original_and_partial_refund",
    ),
    pytest.param(
        create_and_adjust_to_exceed_original_and_full_refund_test_data,
        id="create_and_adjust_to_exceed_original_and_full_refund",
    ),
]


@pytest.fixture(autouse=True)
def enable_stripe_outbound(stripe_api: StripeAPISettings):
    stripe_api.enable_outbound()


@pytest.fixture(autouse=True)
def override_capture_delay(app_context: AppContext):
    original_capture_service_delay = (
        app_context.capture_service.default_capture_delay_in_minutes
    )
    app_context.capture_service.default_capture_delay_in_minutes = 0
    yield
    app_context.capture_service.default_capture_delay_in_minutes = (
        original_capture_service_delay
    )


class CapturePaymentIntentTestBase(ABC):
    async def _test_cart_payment_state_transition(
        self,
        cart_payment_states: List[CartPaymentState],
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        # 1. Prepare and verify initial CartPayment:
        init_cart_payment_state = cart_payment_states[0]
        init_cart_payment = await self._prepare_cart_payment(
            payer=payer,
            payment_method=payment_method,
            cart_payment_processor=cart_payment_processor,
        )

        assert (
            init_cart_payment.amount == init_cart_payment_state.expected_amount
        ), f"cart payment amount as expected {init_cart_payment_state}"

        init_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
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
                    f"Failed cart payment state change: {new_cart_payment_state}"
                ) from e

    async def _update_and_verify_cart_payment_states(
        self,
        init_cart_payment: CartPayment,
        consumer_charge_id: int,
        new_cart_payment_state: CartPaymentState,
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
    ):
        pre_update_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            cart_payment_id=init_cart_payment.id
        )
        id_to_pre_update_payment_intents = {
            pi.id: pi for pi in pre_update_payment_intents
        }

        adjustment_idempotency_key = (
            None
        )  # presence of idempotency_key means whether there is adjustment
        if new_cart_payment_state.amnt_delta_update:
            cart_payment_pre_update, _ = await cart_payment_repository.get_cart_payment_by_id(
                init_cart_payment.id
            )
            assert (
                cart_payment_pre_update
            ), "expect cart_payment already exists before update!"
            amount_delta_to_update = new_cart_payment_state.amnt_delta_update
            adjustment_idempotency_key = str(uuid4())
            await self._update_cart_payment(
                cart_payment_processor=cart_payment_processor,
                existing_cart_payment=cart_payment_pre_update,
                idempotency_key=adjustment_idempotency_key,
                payer_id=cart_payment_pre_update.payer_id,
                delta_amount=amount_delta_to_update,
                consumer_charge_id=consumer_charge_id,
            )
        elif new_cart_payment_state.capture_intents:
            await self._capture_intents(
                cart_payment_repository=cart_payment_repository,
                cart_payment_processor=cart_payment_processor,
            )

        updated_cart_payment, _ = await cart_payment_repository.get_cart_payment_by_id(
            init_cart_payment.id
        )

        assert isinstance(updated_cart_payment, CartPayment)
        assert (
            updated_cart_payment.amount == new_cart_payment_state.expected_amount
        ), "updated_cart_payment amount mismatch"

        updated_payment_intents = await cart_payment_repository.get_payment_intents_for_cart_payment(
            updated_cart_payment.id
        )
        updated_payment_intents.sort(key=lambda pi: pi.created_at)

        for payment_intent, payment_intent_state in zip(
            updated_payment_intents, new_cart_payment_state.payment_intent_states
        ):
            # verify new path
            assert (
                payment_intent.amount == payment_intent_state.amnt
            ), "payment_intent amount mismatch"
            assert (
                payment_intent.status == payment_intent_state.status
            ), "payment_intent status mismatch"
            pgp_payment_intents = await cart_payment_repository.find_pgp_payment_intents(
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
                payment_intent_adjustment_history = await cart_payment_repository.get_payment_intent_adjustment_history(
                    payment_intent.id, adjustment_idempotency_key
                )
                pre_update_payment_intent: PaymentIntent = id_to_pre_update_payment_intents[
                    payment_intent.id
                ]
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
                    payment_intent_adjustment_history.amount == payment_intent.amount
                ), "payment_intent_adjustment_history amount mismatch"

            assert (
                len(pgp_payment_intents) == 1
            ), "number of pgp_payment_intent mismatch"
            assert (
                pgp_payment_intents[0].status
                == payment_intent_state.pgp_payment_intent_state.status
            ), "pgp_payment_intent staus mismatch"
            assert (
                pgp_payment_intents[0].amount
                == payment_intent_state.pgp_payment_intent_state.amnt
            ), "pgp_payment_intent amount mismatch"

            # verify legacy path
            consumer_charge, stripe_charge = await cart_payment_processor.legacy_payment_interface.find_existing_payment_charge(
                charge_id=payment_intent.legacy_consumer_charge_id,
                idempotency_key=payment_intent.idempotency_key,
            )
            assert consumer_charge, "consumer charge not found!"
            assert stripe_charge, "stripe charge not found!"
            assert (
                consumer_charge.original_total == init_cart_payment.amount
            ), "consumer charge amount always = init cart payment amount"
            assert (
                stripe_charge.amount == payment_intent_state.stripe_charge_state.amnt
            ), "stripe charge amount mismatch"
            assert (
                stripe_charge.status == payment_intent_state.stripe_charge_state.status
            ), "stripe charge status mismatch"
            assert (
                stripe_charge.amount_refunded
                == payment_intent_state.stripe_charge_state.amnt_refunded
            ), "stripe charge amount_refunded mismatch"

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
        pgp_payment_intents: List[
            PgpPaymentIntent
        ] = await cart_payment_repository.find_pgp_payment_intents(payment_intent.id)
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
        cart_payment_processor: CartPaymentProcessor,
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


class TestCapturePaymentIntent(CapturePaymentIntentTestBase):
    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    @pytest.mark.parametrize(
        "cart_payment_states", cart_payment_delay_capture_state_transit_tests
    )
    async def test_cart_payment_state_transit(
        self,
        cart_payment_states: List[CartPaymentState],
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        await super()._test_cart_payment_state_transition(
            cart_payment_states,
            cart_payment_processor,
            cart_payment_repository,
            payer,
            payment_method,
        )

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


class TestCapturePaymentIntentLegacy(CapturePaymentIntentTestBase):
    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    @pytest.mark.parametrize(
        "cart_payment_states", cart_payment_delay_capture_state_transit_tests
    )
    async def test_cart_payment_state_transit(
        self,
        cart_payment_states: List[CartPaymentState],
        cart_payment_processor: CartPaymentProcessor,
        cart_payment_repository: CartPaymentRepository,
        payer: Payer,
        payment_method: PaymentMethod,
    ):
        await super()._test_cart_payment_state_transition(
            cart_payment_states,
            cart_payment_processor,
            cart_payment_repository,
            payer,
            payment_method,
        )

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
        cart_payment_processor: CartPaymentProcessor,
    ) -> CartPayment:
        request = CartPayment(
            id=uuid4(),
            amount=1000,
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
