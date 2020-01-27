from enum import Enum
from typing import List, NewType

LegacyConsumerChargeId = NewType("LegacyConsumerChargeId", int)


class IdempotencyKeyAction(Enum):
    CREATE = "create"
    ADJUST = "adjust"
    CANCEL = "cancel"
    REFUND = "refund"


class CartType(str, Enum):
    UNKNOWN = "Unknown"
    ORDER_CART = "OrderCart"
    DRIVE = "Drive"
    SUBSCRIPTION = "Subscription"


class CaptureMethod(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class IntentStatus(str, Enum):
    INIT = "init"
    PENDING = "doordash_pending"  # keeping as this for backwards compatibility
    PROCESSING = "processing"
    REQUIRES_CAPTURE = "requires_capture"
    CAPTURE_FAILED = "capture_failed"
    CAPTURING = "capturing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    # TODO PAYIN-130 update "cancelled" in payin domain to "canceled" to sync with stripe
    @classmethod
    def from_str(cls, value: str) -> "IntentStatus":
        if value in ["canceled", "cancelled"]:
            return cls("cancelled")
        return cls(value)

    @classmethod
    def transiting_status(cls) -> List["IntentStatus"]:
        """
        :return: intent statuses that are expected to be moved to next status in state machine
        """
        return [
            st
            for st in IntentStatus
            if st
            not in [IntentStatus.CANCELLED, IntentStatus.FAILED, IntentStatus.SUCCEEDED]
        ]


class RefundStatus(str, Enum):
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RefundReason(str, Enum):
    """
    Refund reasons is a superset of what providers support.  See provider models, such as
    app.commons.providers.stripe.stripe_models.StripeRefundChargeRequest.RefundReason.
    """

    DUPLICATE = "duplicate"
    FRAUDULENT = "fraudulent"
    REQUESTED_BY_CUSTOMER = "requested_by_customer"


class ChargeStatus(str, Enum):
    REQUIRES_CAPTURE = "requires_capture"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LegacyStripeChargeStatus(str, Enum):
    PENDING = "doordash_pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING_FAILED = "doordash_pending_failed"
    PENDING_REFUNDED = "doordash_pending_refunded"
