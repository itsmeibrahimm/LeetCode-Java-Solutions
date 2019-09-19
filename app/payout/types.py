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


STRIPE_TRANSFER_FAILED_STATUS = "failed"
UNKNOWN_ERROR_STR = "err"


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


class StripeTransferSubmissionStatus(str, Enum):
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    UNKNOWN = "unknown"
    FAILED_TO_SUBMIT = "failed_to_submit"


class StripeErrorCode(str, Enum):
    NO_EXT_ACCOUNT_IN_CURRENCY = "no_external_account_in_currency"
    PAYOUT_NOT_ALLOWED = "payouts_not_allowed"
    INVALID_REQUEST_ERROR = "invalid_request_error"
