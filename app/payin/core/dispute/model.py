from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from typing_extensions import final


class StripeDispute(BaseModel):
    id: int
    stripe_dispute_id: str
    disputed_at: datetime
    amount: int
    fee: int
    net: int
    charged_at: datetime
    reason: str
    status: str
    evidence_due_by: datetime
    stripe_card_id: int
    stripe_charge_id: int
    currency: Optional[str] = None
    evidence_submitted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@final
class Dispute(StripeDispute):
    pass


class Evidence(BaseModel):
    access_activity_log: Optional[str] = None
    billing_address: Optional[str] = None
    cancellation_policy: Optional[str] = None
    cancellation_policy_disclosure: Optional[str] = None
    cancellation_rebuttal: Optional[str] = None
    customer_communication: Optional[str] = None
    customer_email_address: Optional[str] = None
    customer_name: Optional[str] = None
    customer_purchase_ip: Optional[str] = None
    customer_signature: Optional[str] = None
    duplicate_charge_documentation: Optional[str] = None
    duplicate_charge_explanation: Optional[str] = None
    duplicate_charge_id: Optional[str] = None
    product_description: Optional[str] = None
    receipt: Optional[str] = None
    refund_policy: Optional[str] = None
    refund_policy_disclosure: Optional[str] = None
    refund_refusal_explanation: Optional[str] = None
    service_date: Optional[str] = None
    service_documentation: Optional[str] = None
    shipping_address: Optional[str] = None
    shipping_carrier: Optional[str] = None
    shipping_date: Optional[str] = None
    shipping_documentation: Optional[str] = None
    shipping_tracking_number: Optional[str] = None
    uncategorized_file: Optional[str] = None
    uncategorized_text: Optional[str] = None


class DisputeList(BaseModel):
    count: int
    has_more: bool  # Currently default to False. Returning all the disputes for a query
    total_amount: int
    data: List[Dispute]


class DisputeChargeMetadata(BaseModel):
    dd_order_cart_id: str
    dd_charge_id: str
    dd_consumer_id: str
    stripe_card_id: str
    stripe_dispute_status: str
    stripe_dispute_reason: str
