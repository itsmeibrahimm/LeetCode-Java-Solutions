# Account
CREATE_STRIPE_ACCOUNT_TYPE = "custom"
CREATE_STRIPE_ACCOUNT_REQUESTED_CAPABILITIES = ["legacy_payments"]

# Transaction
TRANSACTION_REVERSAL_PREFIX = "txn-void"

# Pagination
# DasherShiftListView list maximum 200 shift therefore we put 200 as the default size for fetch transactions by ids
DEFAULT_PAGE_SIZE = 200

# Transfer
MAX_TRANSFER_AMOUNT_IN_CENTS = 100 * 25000
MAX_TRANSFER_AMOUNT_IDR = (
    344812500
)  # This is about 25,000 US dollars (which is the MAX_TRANSFER_AMOUNT_IN_CENTS)

DAYS_FOR_RECENT_BANK_CHANGE_FOR_LARGE_TRANSFERS_CHECK = (
    "days_for_recent_bank_change_for_large_transfers_check"
)
FF_CHECK_FOR_RECENT_BANK_CHANGE = "FF_CHECK_FOR_RECENT_BANK_CHANGE"

CURRENCY_TO_MAX_TRANSFER_AMOUNT_IN_BASE_UNIT = {
    "USD": MAX_TRANSFER_AMOUNT_IN_CENTS,
    "CAD": MAX_TRANSFER_AMOUNT_IN_CENTS,
    "IDR": MAX_TRANSFER_AMOUNT_IDR,
    "SGD": MAX_TRANSFER_AMOUNT_IN_CENTS,
}
DISABLE_DASHER_PAYMENT_ACCOUNT_LIST_NAME = (
    "DISABLE_DASHER_PAYMENT_ACCOUNT_AUTO_PAYMENT_LIST"
)
DISABLE_MERCHANT_PAYMENT_ACCOUNT_LIST_NAME = (
    "DISABLE_MERCHANT_PAYMENT_ACCOUNT_AUTO_PAYMENT_LIST"
)

DEFAULT_USER_EMAIL_FOR_SUPERPOWERS = "20156288"  # niket@doordash.com

# Fraud related runtime for creating transfers
FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE = (
    "fraud_enable_mx_payout_delay_after_bank_change"
)
FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE = (
    "fraud_business_whitelist_for_payout_delay_after_bank_change"
)
FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE = (
    "fraud_minimum_hours_before_mx_payout_after_bank_change"
)

PAYOUT_ACCOUNT_LOCK_DEFAULT_TIMEOUT = 60  # in second
