import pydantic
import datetime
from enum import Enum
from typing import List, Optional

from app.commons.types import CountryCode, CurrencyType
from app.payout.types import (
    PayoutAccountId,
    PayoutAccountToken,
    PayoutMethodId,
    PayoutMethodToken,
    PayoutId,
)

__all__ = ["PayoutAccountId", "PayoutAccountToken"]


class PayoutAccountTargetType(str, Enum):
    Dasher = "dasher"
    Store = "store"


PayoutAccountTargetId = int  # NewType("PayoutAccountTargetId", int)


class CreatePayoutAccount(pydantic.BaseModel):
    country: CountryCode
    target_type: PayoutAccountTargetType
    target_id: PayoutAccountTargetId


class PayoutAccount(pydantic.BaseModel):
    id: PayoutAccountId
    stripe_managed_account_id: str
    entity: str
    statement_descriptor: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    verification_requirements: List[str]
    payout_enabled_status: bool


class PayoutAccountDetails(PayoutAccount):
    verification_status: str


class VerificationDetails(pydantic.BaseModel):
    class DateOfBirth(pydantic.BaseModel):
        day: int
        month: int
        year: int

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[DateOfBirth] = None
    ...


class CreatePayoutMethod(pydantic.BaseModel):
    token: PayoutMethodToken


class PayoutMethod(pydantic.BaseModel):
    """
    Bank or Debit Card
    """

    id: PayoutMethodId
    ...


class PayoutRequestMethod(str, Enum):
    Standard = "standard"
    Instant = "instant"


class PayoutRequest(pydantic.BaseModel):
    amount: int
    currency: CurrencyType
    method: PayoutRequestMethod = PayoutRequestMethod.Standard


class Payout(PayoutRequest):
    id: PayoutId
