from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any

from pydantic import BaseModel
from typing_extensions import final
from app.payin.core.cart_payment.types import (
    IntentStatus,
    ChargeStatus,
    LegacyConsumerChargeId,
)
from uuid import UUID

from app.payin.core.types import PgpPaymentMethodResourceId, PgpPayerResourceId


@final
class LegacyPayment(BaseModel):
    dd_consumer_id: int
    dd_country_id: Optional[int] = None
    dd_stripe_card_id: Optional[int] = None
    dd_additional_payment_info: Optional[Dict[str, Any]] = None
    stripe_charge_id: Optional[str] = None
    stripe_customer_id: Optional[PgpPayerResourceId] = None
    stripe_card_id: Optional[PgpPaymentMethodResourceId] = None


@final
class CorrelationIds(BaseModel):
    reference_id: str
    reference_type: str


@final
class SplitPayment(BaseModel):
    payout_account_id: str
    application_fee_amount: int


class CartPayment(BaseModel):
    id: UUID
    amount: int
    payer_id: Optional[UUID]
    payment_method_id: Optional[UUID]
    delay_capture: bool
    correlation_ids: CorrelationIds
    metadata: Optional[Dict[str, Any]]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    client_description: Optional[str] = None
    payer_statement_description: Optional[str] = None
    split_payment: Optional[SplitPayment] = None
    capture_after: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


@final
class PaymentIntent(BaseModel):
    id: UUID
    cart_payment_id: UUID
    idempotency_key: str
    amount_initiated: int
    amount: int
    amount_capturable: Optional[int]  # TODO fix use of this field
    amount_received: Optional[int]
    application_fee_amount: Optional[int]
    capture_method: str
    country: str
    currency: str
    status: IntentStatus
    statement_descriptor: Optional[str]
    payment_method_id: Optional[UUID]
    metadata: Optional[Dict[str, Any]]
    legacy_consumer_charge_id: LegacyConsumerChargeId
    created_at: datetime
    updated_at: datetime
    captured_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    capture_after: Optional[datetime]


@final
@dataclass(frozen=True)
class PgpPaymentIntent:
    id: UUID
    payment_intent_id: UUID
    idempotency_key: str
    provider: str
    resource_id: Optional[str]
    status: IntentStatus
    invoice_resource_id: Optional[str]
    charge_resource_id: Optional[str]
    payment_method_resource_id: str
    customer_resource_id: Optional[str]
    currency: str
    amount: int
    amount_capturable: Optional[int]
    amount_received: Optional[int]
    application_fee_amount: Optional[int]
    payout_account_id: Optional[str]
    capture_method: str
    created_at: datetime
    updated_at: datetime
    captured_at: Optional[datetime]
    cancelled_at: Optional[datetime]


@final
@dataclass(frozen=True)
class PaymentIntentAdjustmentHistory:
    id: UUID
    payer_id: Optional[UUID]
    payment_intent_id: UUID
    amount: int
    amount_original: int
    amount_delta: int
    currency: str
    created_at: datetime


@final
@dataclass(frozen=True)
class PaymentCharge:
    id: UUID
    payment_intent_id: UUID
    provider: str
    idempotency_key: str
    status: ChargeStatus
    currency: str
    amount: int
    amount_refunded: int
    application_fee_amount: Optional[int]
    payout_account_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    captured_at: Optional[datetime]
    cancelled_at: Optional[datetime]


@final
@dataclass(frozen=True)
class PgpPaymentCharge:
    id: UUID
    payment_charge_id: UUID
    provider: str
    idempotency_key: str
    status: ChargeStatus
    currency: str
    amount: int
    amount_refunded: int
    application_fee_amount: Optional[int]
    payout_account_id: Optional[str]
    resource_id: Optional[str]
    intent_resource_id: Optional[str]
    invoice_resource_id: Optional[str]
    payment_method_resource_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    captured_at: Optional[datetime]
    cancelled_at: Optional[datetime]


@final
@dataclass
class LegacyConsumerCharge:
    id: LegacyConsumerChargeId
    target_id: int
    target_ct_id: int
    idempotency_key: str
    is_stripe_connect_based: bool
    total: int
    original_total: int
    currency: str
    country_id: int
    issue_id: Optional[int]
    stripe_customer_id: Optional[int]
    created_at: datetime


@final
@dataclass()
class LegacyStripeCharge:
    id: int
    amount: int
    amount_refunded: int
    currency: str
    status: str
    error_reason: Optional[str]
    additional_payment_info: Optional[str]
    description: Optional[str]
    idempotency_key: str
    card_id: Optional[int]
    charge_id: int
    stripe_id: str
    created_at: datetime
    updated_at: datetime
    refunded_at: Optional[datetime]
