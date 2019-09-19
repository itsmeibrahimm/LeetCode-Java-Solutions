from typing import Optional

from app.commons.api.models import PaymentRequest, PaymentResponse
from app.commons.types import CountryCode, CurrencyType
from app.payout.core.account.types import DateOfBirth, Address
from app.payout.types import (
    PayoutAccountId,
    PayoutAccountToken,
    PayoutMethodId,
    PayoutMethodToken,
    PayoutAccountTargetType,
    PayoutAccountTargetId,
    PgpAccountId,
    StripeFileHandle,
    PayoutAmountType,
    PayoutType,
    PayoutMethodType,
    PayoutTargetType,
    PgpExternalAccountId,
    StripeAccountToken,
    StripeBusinessType,
    AccountType,
)
from app.payout.core.account.types import VerificationRequirements

__all__ = ["PayoutAccountId", "PayoutAccount", "PayoutAccountToken"]


class CreatePayoutAccount(PaymentRequest):
    target_id: PayoutAccountTargetId
    target_type: PayoutAccountTargetType
    country: CountryCode
    currency: CurrencyType
    statement_descriptor: Optional[str]


class PayoutAccount(PaymentResponse):
    id: PayoutAccountId
    statement_descriptor: str
    pgp_account_type: Optional[AccountType]
    pgp_account_id: Optional[PgpAccountId]
    pgp_external_account_id: Optional[PgpExternalAccountId]
    verification_requirements: Optional[VerificationRequirements]
    # todo: add payout_methods, payout_schedule


class VerificationDetails(PaymentRequest):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[DateOfBirth] = None
    business_name: Optional[str] = None
    business_tax_id: Optional[str] = None
    address: Optional[Address] = None
    id_file: Optional[StripeFileHandle] = None
    personal_identification_number: Optional[str] = None
    ssn_last_four: Optional[str] = None
    business_type: Optional[StripeBusinessType] = None
    # we need pass in country and currency to create stripe account unless payment account table can store them
    country: CountryCode
    currency: CurrencyType


class VerificationDetailsWithToken(PaymentRequest):
    account_token: StripeAccountToken
    # we need pass in country and currency to create stripe account unless payment account table can store them
    country: CountryCode
    currency: CurrencyType


class CreatePayoutMethod(PaymentRequest):
    token: PayoutMethodToken


class PayoutMethod(PaymentResponse):
    """
    Bank or Debit Card
    """

    id: PayoutMethodId
    ...


class PayoutRequest(PaymentRequest):
    amount: PayoutAmountType
    payout_type: PayoutType = PayoutType.STANDARD
    target_id: Optional[str] = None
    target_type: Optional[PayoutTargetType] = None
    statement_descriptor: Optional[str] = None
    payout_idempotency_key: Optional[str] = None
    transfer_id: Optional[str] = None
    payout_id: Optional[str] = None
    method: Optional[PayoutMethodType]
    submitted_by: Optional[str] = None


class Payout(PaymentResponse):
    pass
