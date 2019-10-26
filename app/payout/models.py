from enum import Enum

# Payout Accounts
from app.payout.core.exceptions import PayoutErrorCode

PayoutAccountId = int  # NewType("PayoutAccountId", int)
PayoutAccountToken = str
PayoutAccountTargetId = int
PayoutAccountStatementDescriptor = str


class CommaSeperatedArrayStr(str):
    def __init__(self, str):
        self.str = str

    def __to_array__(self):
        return self.str.split(",")


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

TRANSFER_METHOD_TO_SUBMIT_FUNCTION = {
    TransferMethodType.STRIPE: "_submit_stripe_transfer",
    TransferMethodType.CHECK: "_submit_check_transfer",
    TransferMethodType.BANK: None,
    TransferMethodType.STRIPE_FAST_PAY: None,
}


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
TransactionTargetId = int


class TransactionTargetType(str, Enum):
    MERCHANT_DELIVERY = "merchant_delivery"
    DASHER_JOB = "dasher_job"
    DASHER_SHIFT = "dasher_shift"
    DASHER_DELIVERY = "dasher_delivery"
    DELIVERY_ERROR = "delivery_error"
    DELIVERY_RECEIPT = "delivery_receipt"
    STORE_PAYMENT = "store_payment"
    VEHICLE_PARTNER_PAYMENT = "vehicle_partner_payment"
    PAYOUT_FEE = "payout_fee"
    MICRO_DEPOSIT = "micro_deposit"


class TransactionState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CANCELLED = "cancelled"
