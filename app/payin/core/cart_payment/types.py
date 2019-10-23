from enum import Enum
from typing import NewType

LegacyConsumerChargeId = NewType("LegacyConsumerChargeId", int)


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

    # todo PAYIN-130 update "cancelled" in payin domain to "canceled" to sync with stripe
    @classmethod
    def from_str(cls, value: str) -> "IntentStatus":
        if value in ["canceled", "cancelled"]:
            return cls("cancelled")
        return cls(value)


class RefundStatus(str, Enum):
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ChargeStatus(str, Enum):
    REQUIRES_CAPTURE = "requires_capture"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LegacyStripeChargeStatus(str, Enum):
    PENDING = "doordash_pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
