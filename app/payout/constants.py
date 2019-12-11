# Account
CREATE_STRIPE_ACCOUNT_TYPE = "custom"
CREATE_STRIPE_ACCOUNT_REQUESTED_CAPABILITIES = ["legacy_payments"]
DEFAULT_STATEMENT_DESCRIPTOR = "DoorDash, Inc."

# Transaction
TRANSACTION_REVERSAL_PREFIX = "txn-void"

# Pagination
# DasherShiftListView list maximum 200 shift therefore we put 200 as the default size for fetch transactions by ids
DEFAULT_PAGE_SIZE_TRANSACTIONS = 1000

# Transfer
MAX_TRANSFER_AMOUNT_IN_CENTS = 100 * 25000
MAX_TRANSFER_AMOUNT_IDR = (
    344812500
)  # This is about 25,000 US dollars (which is the MAX_TRANSFER_AMOUNT_IN_CENTS)

DAYS_FOR_RECENT_BANK_CHANGE_FOR_LARGE_TRANSFERS_CHECK = (
    "payout/feature-flags/days_for_recent_bank_change_for_large_transfers_check.int"
)
FF_CHECK_FOR_RECENT_BANK_CHANGE = (
    "payout/feature-flags/FF_CHECK_FOR_RECENT_BANK_CHANGE.bool"
)

CURRENCY_TO_MAX_TRANSFER_AMOUNT_IN_BASE_UNIT = {
    "USD": MAX_TRANSFER_AMOUNT_IN_CENTS,
    "CAD": MAX_TRANSFER_AMOUNT_IN_CENTS,
    "IDR": MAX_TRANSFER_AMOUNT_IDR,
    "SGD": MAX_TRANSFER_AMOUNT_IN_CENTS,
}
DISABLE_DASHER_PAYMENT_ACCOUNT_LIST_NAME = (
    "payout/feature-flags/DISABLE_DASHER_PAYMENT_ACCOUNT_AUTO_PAYMENT_LIST.json"
)
DISABLE_MERCHANT_PAYMENT_ACCOUNT_LIST_NAME = (
    "payout/feature-flags/DISABLE_MERCHANT_PAYMENT_ACCOUNT_AUTO_PAYMENT_LIST.json"
)

DEFAULT_USER_EMAIL_FOR_SUPERPOWERS = "20156288"  # niket@doordash.com

# transfer submission
ATTEMPTED_COUNT_STAT = "attempted-count"
ATTEMPTED_AMOUNT_STAT = "attempted-amount"
SUCCEEDED_COUNT_STAT = "succeeded-count"
SUCCEEDED_AMOUNT_STAT = "succeeded-amount"

# monitoring tasks
MONITORING_PREFIX = "payment-service.tasks.monitoring"
BACKFILL_MONITORING_PREFIX = MONITORING_PREFIX + ".backfill"


def backfill_tasks_monitoring_stat_name(stat_name):
    return BACKFILL_MONITORING_PREFIX + "." + stat_name


def transfer_submission_monitoring_stat_name(entity, stat_name):
    return MONITORING_PREFIX + ".transfer-submission." + entity + "." + stat_name


UPDATED_INCORRECT_STRIPE_TRANSFER_STATUS = backfill_tasks_monitoring_stat_name(
    "update-incorrect-stripe-transfer-status"
)

# Fraud related runtime for creating transfers
FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE = (
    "payout/feature-flags/fraud_enable_mx_payout_delay_after_bank_change.bool"
)
FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE = "payout/feature-flags/fraud_business_whitelist_for_payout_delay_after_bank_change.json"
FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE = (
    "payout/feature-flags/fraud_minimum_hours_before_mx_payout_after_bank_change.int"
)

PAYOUT_ACCOUNT_LOCK_DEFAULT_TIMEOUT = 60  # in second
FRAUD_MX_AUTO_PAYMENT_DELAYED_RECENT_BANK_CHANGE = (
    "fraud.mx_auto_payment_delayed.recent_bank_change"
)
