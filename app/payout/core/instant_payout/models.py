from datetime import datetime
from enum import Enum
from typing import Optional

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
    PAYOUT_ACCOUNT_NOT_EXIST = "Payout account does not exist."
    PAYOUT_ACCOUNT_TYPE_NOT_SUPPORTED = "Payout account type not supported."
    PAYOUT_PGP_ACCOUNT_NOT_SETUP = "Payout PGP account not setup."
    PAYOUT_PGP_ACCOUNT_NOT_EXIST = "Payout PGP account not exist."
    PAYOUT_ACCOUNT_COUNTRY_NOT_SUPPORTED = "Payout country not supported."
    PAYOUT_PGP_ACCOUNT_NOT_VERIFIED = "Payout pgp account not verified."
    PAYOUT_CARD_NOT_SETUP = "Payout card not setup."
    PAYOUT_CARD_CHANGED_RECENTLY = "Payout card changed recently."
    INSUFFICIENT_BALANCE = "Balance insufficient"
    ALREADY_PAID_OUT_TODAY = "Already paid out today."


class EligibilityCheckRequest(OperationRequest):
    payout_account_id: int
    created_after: Optional[datetime]


class InternalPaymentEligibility(OperationResponse):
    eligible: bool
    reason: Optional[str]
    details: Optional[dict]
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
