from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from app.commons.core.processor import OperationResponse
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.types import PgpExternalAccountId


class VerificationStatus(str, Enum):
    BLOCKED = "blocked"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


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
