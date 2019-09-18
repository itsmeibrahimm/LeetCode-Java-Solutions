from enum import Enum

# Payout Accounts
PayoutAccountId = int  # NewType("PayoutAccountId", int)
PayoutAccountToken = str
PayoutAccountTargetId = int
PayoutAccountStatementDescriptor = str

PgpAccountId = int
PgpExternalAccountId = str

StripeFileHandle = str
StripeAccountToken = str

# Payout Methods
PayoutMethodId = str
PayoutMethodToken = str

# Payouts
PayoutId = str
PayoutAmountType = int


class PayoutAccountTargetType(str, Enum):
    DASHER = "dasher"
    STORE = "store"


class PgpAccountType(str, Enum):
    STRIPE = "stripe_managed_account"


class StripeBusinessType(str, Enum):
    COMPANY = "company"
    INDIVIDUAL = "individual"


class PayoutType(str, Enum):
    STANDARD = "standard"
    INSTANT = "instant"


class PayoutMethodType(str, Enum):
    STRIPE = "stripe"


class PayoutTargetType(str, Enum):
    DASHER = "dasher"
    STORE = "store"


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


class AccountType(str, Enum):
    # payment_account.account_type
    ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT = "stripe_managed_account"


class PayoutExternalAccountType(str, Enum):
    CARD = "card"
