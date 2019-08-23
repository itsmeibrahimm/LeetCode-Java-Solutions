from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from typing_extensions import final
from app.payin.core.cart_payment.types import CartType, IntentStatus, ChargeStatus
from uuid import UUID


@final
@dataclass(frozen=True)
class LegacyPayment:
    consumer_id: int
    charge_id: int
    stripe_customer_id: Optional[int] = None


@final
@dataclass(frozen=True)
class SplitPayment:
    payout_account_id: str
    application_fee_amount: int


@final
@dataclass(frozen=True)
class CartMetadata:
    reference_id: int
    ct_reference_id: int
    type: CartType


@dataclass
class CartPayment:
    id: UUID
    amount: int
    payer_id: str
    payment_method_id: Optional[str]
    capture_method: Optional[str]
    cart_metadata: CartMetadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    client_description: Optional[str] = None
    payer_statement_description: Optional[str] = None
    legacy_payment: Optional[LegacyPayment] = None
    split_payment: Optional[SplitPayment] = None
    deleted_at: Optional[datetime] = None


@final
@dataclass(frozen=True)
class PaymentIntent:
    id: UUID
    cart_payment_id: UUID
    idempotency_key: str
    amount_initiated: int
    amount: int
    amount_capturable: int
    amount_received: int
    application_fee_amount: int
    capture_method: str
    confirmation_method: str
    country: str
    currency: str
    status: IntentStatus
    statement_descriptor: str
    created_at: datetime
    updated_at: datetime
    captured_at: Optional[datetime]
    cancelled_at: Optional[datetime]


@final
@dataclass(frozen=True)
class PgpPaymentIntent:
    id: UUID
    payment_intent_id: UUID
    idempotency_key: str
    provider: str
    resource_id: str
    status: IntentStatus
    invoice_resource_id: Optional[str]
    charge_resource_id: Optional[str]
    payment_method_resource_id: str
    currency: str
    amount: int
    amount_capturable: int
    amount_received: int
    application_fee_amount: Optional[int]
    payout_account_id: Optional[str]
    capture_method: str
    confirmation_method: str
    created_at: datetime
    updated_at: datetime
    captured_at: Optional[datetime]
    cancelled_at: Optional[datetime]


@final
@dataclass(frozen=True)
class PaymentIntentAdjustmentHistory:
    id: UUID
    payer_id: str
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
