#  type: ignore

from datetime import datetime
from typing import List, Optional
from pydantic import Schema

from app.commons.api.models import PaymentRequest, PaymentResponse
from app.commons.types import CountryCode, Currency
from app.payout.core.account.models import (
    Address,
    DateOfBirth,
    VerificationRequirements,
)
from app.payout.models import (
    PayoutAccountId,
    PayoutAccountToken,
    PayoutMethodId,
    PayoutMethodExternalAccountToken,
    PayoutAccountTargetType,
    PayoutAccountTargetId,
    PayoutAmountType,
    PayoutMethodType,
    PayoutTargetType,
    PayoutType,
    PgpAccountId,
    PgpExternalAccountId,
    StripeAccountToken,
    StripeBusinessType,
    StripeFileHandle,
    AccountType,
    PayoutExternalAccountType,
    PayoutMethodExternalAccountId,
    TransferId,
)

__all__ = [
    "CreatePayoutAccount",
    "CreatePayoutMethod",
    "PayoutAccountId",
    "PayoutAccount",
    "PayoutAccountToken",
    "VerificationDetailsWithToken",
    "UpdatePayoutAccountStatementDescriptor",
]


class UpdatePayoutAccountStatementDescriptor(PaymentRequest):
    """
    Statement descriptor for payouts
    """

    statement_descriptor: str


class CreatePayoutAccount(PaymentRequest):
    """
    Request model for creating a payout account
    """

    target_id: PayoutAccountTargetId = Schema(
        default=...,
        description="The target id (e.g., store id) for the payout account to be created",
    )
    target_type: PayoutAccountTargetType = Schema(
        default=...,
        description="The target type (e.g., store) for the payout account to be created",
    )
    country: CountryCode = Schema(
        default=..., description="The country code for the payout account to be created"
    )
    currency: Currency = Schema(
        default=...,
        description="The currency code for the payout account to be created",
    )
    statement_descriptor: Optional[str] = Schema(
        default=None,
        description="The statement descriptor for the payout account to be created",
    )


class PayoutAccount(PaymentResponse):
    """
    Response model for a payout account
    """

    id: PayoutAccountId = Schema(default=..., description="Payout Account ID")
    statement_descriptor: str = Schema(
        default=..., description="The statement descriptor for the payout account"
    )
    pgp_account_type: Optional[AccountType] = Schema(
        default=None, description="Payout account type"
    )
    pgp_account_id: Optional[PgpAccountId] = Schema(
        default=None, description="Linked payment provider Account ID"
    )
    pgp_external_account_id: Optional[PgpExternalAccountId] = Schema(
        default=None, description="Linked external payment provider account ID"
    )
    verification_requirements: Optional[VerificationRequirements] = Schema(
        default=None, description="Required info to pass account verification"
    )
    # todo: add payout_methods, payout_schedule


class PayoutAccountStream(PaymentResponse):
    cursor: Optional[str]
    items: List[PayoutAccount]


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
    """
    Request model for account verification info with token, country and currency
    """

    account_token: StripeAccountToken = Schema(
        default=..., description="Token for the account info for verification"
    )
    # we need pass in country and currency to create stripe account unless payment account table can store them
    country: CountryCode = Schema(default=..., description="Account country")
    currency: Currency = Schema(default=..., description="Account currency")


class CreatePayoutMethod(PaymentRequest):
    """
    Request model for payout method
    """

    token: PayoutMethodExternalAccountToken = Schema(
        default=..., description="Token for the payout method"
    )
    type: PayoutExternalAccountType = Schema(
        default=..., description="Payout method type"
    )


class PayoutMethod(PaymentResponse):
    """
    Response model of generic payout method
    """

    id: PayoutMethodId = Schema(default=..., description="Payout method ID")
    type: PayoutExternalAccountType = Schema(
        default=..., description="Payout method type"
    )
    payout_account_id: PayoutAccountId = Schema(
        default=..., description="Payout Account ID"
    )
    country: CountryCode = Schema(default=..., description="Country Code")
    currency: Currency = Schema(default=..., description="Currency Code")
    created_at: datetime = Schema(default=..., description="Created at timestamp")
    updated_at: datetime = Schema(default=..., description="Updated at timestamp")
    deleted_at: Optional[datetime] = Schema(
        default=None, description="Deleted at timestamp"
    )


class PayoutMethodCard(PayoutMethod):
    """
    Response model of payout method (card type)
    """

    stripe_card_id: PayoutMethodExternalAccountId = Schema(
        default=..., description="External Card ID"
    )
    last4: str = Schema(default=..., description="Card last 4 digits")
    brand: str = Schema(default=..., description="Card brand")
    is_default: bool = Schema(default=..., description="Is default boolean")
    exp_month: int = Schema(default=..., description="Exp month")
    exp_year: int = Schema(default=..., description="Exp year")
    fingerprint: str = Schema(default=..., description="Card fingerprint")


class PayoutMethodBankAccount(PayoutMethod):
    """
    Response model of payout method (bank type)
    """

    bank_name: str = Schema(default=..., description="Bank name")
    bank_last_4: str = Schema(default=..., description="Bank last 4 digits")
    fingerprint: str = Schema(default=..., description="Bank account fingerprint")


class InitiatePayoutRequest(PaymentRequest):
    """
    Request model of initiating a payout
    """

    amount: PayoutAmountType = Schema(
        default=..., description="Amount in cents to be paid out"
    )
    payout_type: PayoutType = Schema(default=..., description="Payout type")
    target_id: Optional[str] = Schema(
        default=None, description="Target id of the payout"
    )
    target_type: Optional[PayoutTargetType] = Schema(
        default=None, description="Target type of the payout"
    )
    statement_descriptor: Optional[str] = Schema(
        default=None, description="Statement descriptor for the payout"
    )
    payout_idempotency_key: Optional[str] = Schema(
        default=None, description="Idempotency key of the payout"
    )
    method: Optional[PayoutMethodType] = Schema(
        default=None, description="Payout method"
    )
    submitted_by: Optional[str] = Schema(default=None, description="Submitted by")
    transfer_id: Optional[TransferId] = Schema(default=None, description="Transfer ID")
    payout_id: Optional[str] = Schema(default=None, description="Payout ID")


class Payout(PaymentResponse):
    """
    Response model of creating a payout
    """

    id: Optional[int] = Schema(default=..., description="Payout ID")


class ListPayoutMethod(PaymentRequest):
    limit: Optional[int]
    payout_method_type: Optional[PayoutExternalAccountType]


class PayoutMethodList(PaymentResponse):
    """
    Response model of payout method list
    """

    count: int = Schema(default=..., description="Number of results returned")
    card_list: List[PayoutMethodCard] = Schema(default=..., description="List of cards")
