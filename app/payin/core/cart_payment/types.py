from enum import Enum


class CartType(str, Enum):
    UNKNOWN = "Unknown"
    ORDER_CART = "OrderCart"
    DRIVE = "Drive"
    SUBSCRIPTION = "Subscription"


class CaptureMethod(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class ConfirmationMethod(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class IntentStatus(str, Enum):
    INIT = "init"
    PROCESSING = "processing"
    REQUIRES_CAPTURE = "requires_capture"
    CAPTURE_FAILED = "capture_failed"
    CAPTURING = "capturing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChargeStatus(str, Enum):
    REQUIRES_CAPTURE = "requires_capture"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LegacyStripeChargeStatus(str, Enum):
    PENDING = "doordash_pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
