from datetime import datetime
from enum import Enum
from typing import Optional

from app.commons.core.processor import OperationResponse, OperationRequest
from app.commons.types import Currency, CountryCode
from app.payout.models import PayoutAccountTargetType, PgpAccountType


class InstantPayoutStatusType(str, Enum):
    NEW = "new"  # When the instant payout record is created internally
    PENDING = "pending"  # When submitted to PGP
    PAID = "paid"  # When PGP return paid
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


class InstantPayoutFees(int, Enum):
    STANDARD_FEE = 199


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
