from enum import Enum

# Payout Accounts
from app.payout.core.exceptions import PayoutErrorCode

PayoutAccountId = int  # NewType("PayoutAccountId", int)
PayoutAccountToken = str
PayoutAccountTargetId = int
PayoutAccountStatementDescriptor = str


class PayoutAccountTargetType(str, Enum):
    DASHER = "dasher"
    STORE = "store"


class AccountType(str, Enum):
    # payment_account.account_type
    ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT = "stripe_managed_account"


# Pgp Account
PgpAccountId = int
PgpExternalAccountId = str


class PgpAccountType(str, Enum):
    STRIPE = "stripe_managed_account"


# Stripe
StripeFileHandle = str
StripeAccountToken = str


class StripeBusinessType(str, Enum):
    COMPANY = "company"
    INDIVIDUAL = "individual"


class StripePayoutStatus(str, Enum):
    # for dd stripe_transfer
    FAILED = "failed"
    IN_TRANSIT = "in_transit"
    CANCELED = "canceled"
    PAID = "paid"
    PENDING = "pending"


# Payout Methods
PayoutMethodId = int
PayoutMethodExternalAccountToken = str
PayoutMethodExternalAccountId = str


class PayoutMethodType(str, Enum):
    STRIPE = "stripe"


class PayoutExternalAccountType(str, Enum):
    CARD = "card"


# Payouts
TransferId = int
PayoutId = int
PayoutAmountType = int

STRIPE_TRANSFER_FAILED_STATUS = "failed"
UNKNOWN_ERROR_STR = "err"


class PayoutType(str, Enum):
    STANDARD = "standard"
    INSTANT = "instant"


class PayoutTargetType(str, Enum):
    DASHER = "dasher"
    STORE = "store"


class ManagedAccountTransferStatus(str, Enum):
    FAILED = "failed"
    PAID = "paid"


class StripeTransferSubmissionStatus(str, Enum):
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    UNKNOWN = "unknown"
    FAILED_TO_SUBMIT = "failed_to_submit"


class StripeErrorCode(str, Enum):
    NO_EXT_ACCOUNT_IN_CURRENCY = "no_external_account_in_currency"
    PAYOUT_NOT_ALLOWED = "payouts_not_allowed"
    INVALID_REQUEST_ERROR = "invalid_request_error"


class TransferStatusType(object):
    CREATING = (
        "creating"
    )  # When a Payout is created on DD, but also in the process of updating associated transactions
    CREATED = "created"  # When a Payout is created on stripe side
    NEW = (
        "new"
    )  # When a Payout has been created on DD and ready for submission; Money is still in the SMA balance
    SUBMITTING = (
        "submitting"
    )  # When a Payout has been created on DD, and submission to Stripe is in progress
    PENDING = (
        "pending"
    )  # When a Payout is communicated to Stripe, but communication to Bank still in progress, money has left in SMA balance
    IN_TRANSIT = (
        "in_transit"
    )  # When a Payout has been communicated to the Bank by Stripe
    PAID = "paid"  # When a Payout has deposited money into corresponding bank account
    FAILED = (
        "failed"
    )  # When a Payout failed to deposited to bank account on bank side, money has re-entered SMA balance
    CANCELLED = (
        "cancelled"
    )  # When a Payout is confirmed to have been cancelled, money has re-entered SMA balance
    DELETED = (
        "deleted"
    )  # When a Payout has been manually deleted, money is still in SMA balance.
    ERROR = (
        "error"
    )  # When a Payout fails for a systemic issue e.g. Connection/Timeout/RateLimiting


class TransferStatusCodeType(object):
    ERROR_AMOUNT_LIMIT_EXCEEDED = "amount_limit_exceeded_error"
    ERROR_NO_GATEWAY_ACCOUNT = "no_gateway_account_error"
    ERROR_GATEWAY_ACCOUNT_SETUP = "gateway_account_setup_error"
    ERROR_AMOUNT_MISMATCH = "amount_mismatch_error"
    ERROR_ACCOUNT_ID_MISMATCH = "account_id_mismatch_error"
    ERROR_SUBMISSION = "gateway_submission_error"
    ERROR_INVALID_STATE = "invalid_state"
    UNKNOWN_ERROR = "unknown_error"


class TransferMethodType(object):
    STRIPE = "stripe"
    STRIPE_FAST_PAY = "stripe_fastpay"
    CHECK = "check"
    BANK = "bank"
    DOORDASH_PAY = "doordash_pay"
    COD_INVOICE = (
        "cod_invoice"
    )  # transfer method type for merchants whose payment type is cash_on_delivery


# todo: why this does not have a 1:1 with TransferMethodType??
TRANSFER_METHOD_CHOICES = (
    (TransferMethodType.STRIPE, "Stripe"),
    (TransferMethodType.CHECK, "Check"),
    (TransferMethodType.BANK, "Bank"),
    (TransferMethodType.DOORDASH_PAY, "DoorDash Pay"),
)

TRANSFER_ERROR_TYPE_TO_FAILED_STATUS = [
    PayoutErrorCode.STRIPE_PAYOUT_ACCT_MISSING,
    PayoutErrorCode.STRIPE_PAYOUT_DISALLOWED,
]


class PayoutDay(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"


class TransferType(str, Enum):
    SCHEDULED = "scheduled"
    MICRO_DEPOSIT = "micro_deposit"
    MANUAL = "manual"


# Transactions
TransactionId = int


class TransactionState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CANCELLED = "cancelled"
