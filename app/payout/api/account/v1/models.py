from typing import Optional

from app.commons.api.models import PaymentRequest, PaymentResponse
from app.commons.types import CountryCode, Currency
from app.payout.core.account.types import Address, DateOfBirth, VerificationRequirements
from app.payout.types import (
    AccountType,
    PayoutAccountId,
    PayoutAccountTargetId,
    PayoutAccountTargetType,
    PayoutAccountToken,
    PayoutAmountType,
    PayoutMethodId,
    PayoutMethodToken,
    PayoutMethodType,
    PayoutTargetType,
    PayoutType,
    PgpAccountId,
    PgpExternalAccountId,
    StripeAccountToken,
    StripeBusinessType,
    StripeFileHandle,
)

__all__ = ["PayoutAccountId", "PayoutAccount", "PayoutAccountToken"]


class CreatePayoutAccount(PaymentRequest):
    target_id: PayoutAccountTargetId
    target_type: PayoutAccountTargetType
    country: CountryCode
    currency: Currency
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
    first_name: Optional[str]
    last_name: Optional[str]
    date_of_birth: Optional[DateOfBirth]
    business_name: Optional[str]
    business_tax_id: Optional[str]
    address: Optional[Address]
    id_file: Optional[StripeFileHandle]
    personal_identification_number: Optional[str]
    ssn_last_four: Optional[str]
    business_type: Optional[StripeBusinessType]
    # we need pass in country and currency to create stripe account unless payment account table can store them
    country: CountryCode
    currency: Currency


class VerificationDetailsWithToken(PaymentRequest):
    account_token: StripeAccountToken
    # we need pass in country and currency to create stripe account unless payment account table can store them
    country: CountryCode
    currency: Currency


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
    payout_type: PayoutType
    target_id: Optional[str]
    target_type: Optional[PayoutTargetType]
    statement_descriptor: Optional[str]
    payout_idempotency_key: Optional[str]
    transfer_id: Optional[str]
    payout_id: Optional[str]
    method: Optional[PayoutMethodType]
    submitted_by: Optional[str]


class Payout(PaymentResponse):
    pass
