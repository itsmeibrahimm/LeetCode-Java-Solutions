#  type: ignore

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Json, Schema

from app.commons.core.processor import OperationResponse
from app.commons.types import CountryCode, Currency
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.models import PgpExternalAccountId


class VerificationStatus(str, Enum):
    BLOCKED = "blocked"
    PENDING = "pending"
    VERIFIED = "verified"
    FIELDS_REQUIRED = "fields_required"


class DateOfBirth(BaseModel):
    day: int
    month: int
    year: int


class Address(BaseModel):
    country: CountryCode
    state: str
    city: str
    line1: str
    line2: str
    postal_code: str


class VerificationRequirements(BaseModel):
    """
    Model for required info to pass account verification
    """

    class RequiredFields(BaseModel):
        """
        Model for the Required Fields
        """

        currently_due: List[str] = Schema(
            default=..., description="Currently required fields"
        )
        eventually_due: List[str] = Schema(
            default=..., description="Eventually required fields"
        )
        past_due: List[str] = Schema(
            default=..., description="Past due required fields"
        )

    verification_status: Optional[VerificationStatus] = Schema(
        default=None, description="Current account verification status"
    )
    due_by: Optional[datetime] = Schema(
        default=None, description="Due time for the required info"
    )
    additional_error_info: Optional[str] = Schema(
        default=None, description="Additional error info"
    )
    required_fields: Optional[RequiredFields] = Schema(
        default=None, description="Required fields"
    )


class PayoutAccountInternal(OperationResponse):
    payment_account: PaymentAccount
    pgp_external_account_id: Optional[PgpExternalAccountId]
    verification_requirements: Optional[VerificationRequirements]


class PayoutMethodInternal(OperationResponse):
    # Leave this for Optional until we save bank account in the db
    id: Optional[int]
    token: Optional[UUID]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]


class PayoutCardInternal(PayoutMethodInternal):
    id: int
    token: UUID
    stripe_card_id: str
    payout_account_id: int
    currency: Currency
    country: CountryCode
    last4: str
    brand: str
    exp_month: int
    exp_year: int
    is_default: bool
    fingerprint: str
    created_at: datetime
    updated_at: datetime


class PayoutBankAccountInternal(PayoutMethodInternal):
    payout_account_id: int
    currency: Currency
    country: CountryCode
    bank_last4: str
    bank_name: str
    fingerprint: str


class PayoutMethodListInternal(OperationResponse):
    card_list: List[PayoutCardInternal] = []
    bank_account_list: List[PayoutBankAccountInternal] = []


class VerificationRequirementsOnboarding(OperationResponse):
    required_fields_stages: Json
