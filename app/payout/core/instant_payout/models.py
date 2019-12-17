from datetime import datetime
from enum import Enum
from typing import Optional, List

from app.commons.core.processor import OperationResponse, OperationRequest
from app.commons.providers.stripe.stripe_models import (
    StripeAccountId,
    Destination,
    Amount,
    Currency,
    IdempotencyKey,
)
from app.commons.types import CountryCode
from app.payout.models import PayoutAccountTargetType, PgpAccountType, TransactionState


class InstantPayoutStatusType(str, Enum):
    NEW = "new"  # When the instant payout record is created internally
    PENDING = "pending"  # When submitted to PGP
    PAID = "paid"  # When PGP return paid
    CANCELLED = "cancelled"  # When PGP return cancelled
    CANCELED = (
        "canceled"
    )  # When PGP return canceled (Stripe returning status is `canceled`)
    FAILED = "failed"  # When PGP return failed
    ERROR = "error"  # When there is error submitting instant payout


InstantPayoutDailyLimitCheckStatuses = [
    InstantPayoutStatusType.NEW,
    InstantPayoutStatusType.PENDING,
    InstantPayoutStatusType.PAID,
    InstantPayoutStatusType.FAILED,
]

InstantPayoutSupportedCountries = {CountryCode.US}
InstantPayoutSupportedEntities = {PayoutAccountTargetType.DASHER}
InstantPayoutSupportedPGPAccountTypes = {PgpAccountType.STRIPE}
InstantPayoutCardChangeBlockTimeInDays = 7  # 7 days block

PAYABLE_TRANSACTION_STATES = {None, TransactionState.ACTIVE}


class InstantPayoutFees(int, Enum):
    STANDARD_FEE = 199


InstantPayoutDefaultMethod = "instant"

InstantPayoutDefaultMetaData = {"service_origin": "payment-service"}

InstantPayoutDefaultStatementDescriptor = "Doordash, Inc. FastPay"

InstantPayoutSMATransferDefaultDescription = "Doordash, Inc. SMA Transfer"

InstantPayoutDefaultDescription = "Doordash, Inc. FastPay"


############################################
# Payment Eligibility Request and Response
############################################


class PaymentEligibilityReasons(str, Enum):
    PAYOUT_ACCOUNT_NOT_EXIST = "payout_account_not_exist"
    PAYOUT_ACCOUNT_TYPE_NOT_SUPPORTED = "payout_account_type_not_supported"
    PAYOUT_PGP_ACCOUNT_NOT_SETUP = "payout_pgp_account_not_setup"
    PAYOUT_PGP_ACCOUNT_NOT_EXIST = "payout_pgp_account_not_exist"
    PAYOUT_ACCOUNT_COUNTRY_NOT_SUPPORTED = "payout_account_country_not_supported"
    PAYOUT_PGP_ACCOUNT_NOT_VERIFIED = "payout_pgp_account_not_verified"
    PAYOUT_CARD_NOT_SETUP = "payout_card_not_setup"
    PAYOUT_CARD_CHANGED_RECENTLY = "payout_card_changed_recently"
    INSUFFICIENT_BALANCE = "balance_insufficient"
    ALREADY_PAID_OUT_TODAY = "already_paid_out_today"


payment_eligibility_reason_details = {
    PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST: "The payout account id passed in does not exist.",
    PaymentEligibilityReasons.PAYOUT_ACCOUNT_TYPE_NOT_SUPPORTED: "Instant Payout currently only supports Dasher.",
    PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP: "The payment external service provider account not setup.",
    PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_EXIST: "The payment external service provider account not exist.",
    PaymentEligibilityReasons.PAYOUT_ACCOUNT_COUNTRY_NOT_SUPPORTED: "Instant Payout currently only supports US account.",
    PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_VERIFIED: "The payment external service provider account not verified.",
    PaymentEligibilityReasons.PAYOUT_CARD_NOT_SETUP: "The payout card is not added yet.",
    PaymentEligibilityReasons.INSUFFICIENT_BALANCE: "The balance is not sufficient to perform instant payout.",
    PaymentEligibilityReasons.ALREADY_PAID_OUT_TODAY: "This payout account has already instant paid today.",
}


class EligibilityCheckRequest(OperationRequest):
    payout_account_id: int
    created_after: Optional[datetime]


class InternalPaymentEligibility(OperationResponse):
    payout_account_id: int
    eligible: bool
    reason: Optional[str]
    details: Optional[str]
    balance: Optional[int]
    currency: Optional[Currency]
    fee: Optional[InstantPayoutFees]


class PayoutAccountEligibility(InternalPaymentEligibility):
    pass


class BalanceEligibility(InternalPaymentEligibility):
    pass


class PayoutCardEligibility(InternalPaymentEligibility):
    pass


class InstantPayoutDailyLimitEligibility(InternalPaymentEligibility):
    pass


############################################
# SMA Balance Check Request and Response
############################################


class CheckSMABalanceRequest(OperationRequest):
    stripe_managed_account_id: StripeAccountId
    country: CountryCode


class SMABalance(OperationResponse):
    balance: int


############################################
# Submit SMA Transfer Request and Response
############################################
class SMATransferRequest(OperationRequest):
    payout_id: int
    transaction_ids: list
    amount: Amount
    currency: Currency
    destination: Destination
    country: CountryCode
    idempotency_key: IdempotencyKey


class SMATransferResponse(OperationResponse):
    stripe_transfer_id: str
    stripe_object: str
    amount: Amount
    currency: Currency
    destination: Destination


############################################
# Submit InstantPayout Request and Response
############################################
class SubmitInstantPayoutRequest(OperationRequest):
    payout_id: int
    transaction_ids: list
    country: CountryCode
    stripe_account_id: StripeAccountId
    amount: Amount
    currency: Currency
    payout_method_id: int
    destination: Destination
    idempotency_key: IdempotencyKey


class SubmitInstantPayoutResponse(OperationResponse):
    stripe_payout_id: str
    stripe_object: str
    status: str
    amount: Amount
    currency: Currency
    destination: Destination


#############################################
# Create and Submit Instant Payout Request
# and Response
#############################################
class CreateAndSubmitInstantPayoutRequest(OperationRequest):
    payout_account_id: int
    amount: Amount
    currency: Currency
    card: Optional[str]


class CreateAndSubmitInstantPayoutResponse(OperationResponse):
    payout_account_id: int
    payout_id: int
    amount: Amount
    currency: Currency
    fee: Amount
    status: InstantPayoutStatusType
    card: str
    created_at: datetime


############################################
# Get Payout Card Request and Response
############################################
class GetPayoutCardRequest(OperationRequest):
    payout_account_id: int
    stripe_card_id: Optional[str]


class PayoutCardResponse(OperationResponse):
    payout_card_id: int
    stripe_card_id: str


############################################
# Verify Transactions Request and Response
############################################
class VerifyTransactionsRequest(OperationRequest):
    payout_account_id: int
    amount: Amount


class VerifyTransactionsResponse(OperationResponse):
    transaction_ids: list


############################################
# Create Payout Request and Response
############################################
class CreatePayoutsRequest(OperationRequest):
    payout_account_id: int
    amount: Amount
    currency: Currency
    idempotency_key: IdempotencyKey
    payout_method_id: int
    transaction_ids: list
    fee: InstantPayoutFees


class CreatePayoutsResponse(OperationResponse):
    payout_id: int
    amount: Amount
    fee: Amount
    created_at: datetime


############################################
# Gey Instant Payout Stream Request
############################################
class GetPayoutStreamRequest(OperationRequest):
    payout_account_id: int
    limit: int
    offset: int


class PayoutStreamItem(OperationResponse):
    payout_account_id: int
    payout_id: int
    amount: Amount
    currency: Currency
    fee: Amount
    status: InstantPayoutStatusType
    pgp_payout_id: Optional[str]
    created_at: datetime


class GetPayoutStreamResponse(OperationResponse):
    count: int
    offset: Optional[str]  # new offset
    instant_payouts: List[PayoutStreamItem]
