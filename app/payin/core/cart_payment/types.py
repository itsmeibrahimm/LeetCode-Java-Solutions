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


class Providers(str, Enum):
    STRIPE = "Stripe"


class PaymentIntentStatus(str, Enum):
    INIT = "init"
    PROCESSING = "processing"


class PgpPaymentIntentStatus(str, Enum):
    INIT = ("init",)
    PROCESSING = "processing"
