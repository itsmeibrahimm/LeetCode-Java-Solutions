from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Json

from app.commons.core.processor import OperationResponse
from app.commons.types import CountryCode, Currency
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.types import PgpExternalAccountId


class VerificationStatus(str, Enum):
    BLOCKED = "blocked"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


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
    class RequiredFields(BaseModel):
        currently_due: List[str] = []
        eventually_due: List[str] = []
        past_due: List[str] = []

    verification_status: Optional[VerificationStatus] = None
    due_by: Optional[datetime] = None
    additional_error_info: Optional[str] = None
    required_fields: Optional[RequiredFields] = RequiredFields()


class PayoutAccountInternal(OperationResponse):
    payment_account: PaymentAccount
    pgp_external_account_id: Optional[PgpExternalAccountId]
    verification_requirements: Optional[VerificationRequirements]


class PayoutMethodInternal(OperationResponse):
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


class VerificationRequirementsOnboarding(OperationResponse):
    required_fields_stages: Json
