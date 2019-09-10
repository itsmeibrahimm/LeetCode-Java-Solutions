from enum import Enum

# Payout Accounts
PayoutAccountId = int  # NewType("PayoutAccountId", int)
PayoutAccountToken = str
PayoutAccountTargetId = int
PayoutAccountStatementDescriptor = str


class PayoutAccountTargetType(str, Enum):
    Dasher = "dasher"
    Store = "store"


StripeManagedAccountId = int

StripeFileHandle = str

# Payout Methods
PayoutMethodId = str
PayoutMethodToken = str

# Payouts
PayoutId = str
PayoutAmountType = int


class PayoutType(str, Enum):
    Standard = "standard"
    Instant = "instant"


class PayoutMethodType(str, Enum):
    Stripe = "stripe"


class PayoutTargetType(str, Enum):
    Dasher = "dasher"
    Store = "store"


class StripePayoutStatus(str, Enum):
    # for dd stripe_transfer
    FAILED = "failed"
    IN_TRANSIT = "in_transit"
    CANCELED = "canceled"
    PAID = "paid"
    PENDING = "pending"


class ManagedAccountTransferStatus(str, Enum):
    FAILED = "failed"
    PAID = "paid"
