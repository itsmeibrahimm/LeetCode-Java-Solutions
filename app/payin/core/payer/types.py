from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.types import PayerIdType


class PayerType(str, Enum):
    """
    Enum definition of payer type. Be backward compatible with stripe_customer.owner_type in DSJ.
    """

    MARKETPLACE = "marketplace"
    DRIVE = "drive"
    MERCHANT = "merchant"
    STORE = "store"
    BUSINESS = "business"


class LegacyPayerInfo(BaseModel):
    country: CountryCode
    payer_id: str
    payer_id_type: PayerIdType
    # FIXME: can't enforce payer_type for Drive. This is for lazy creation use and will revisit to see if we can
    # do lazy creation without client input before removing it.
    payer_type: Optional[PayerType]


class DeletePayerRequestStatus(str, Enum):
    IN_PROGRESS = "IN PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class DeletePayerRedactingText(str, Enum):
    REDACTED = "REDACTED"
    XXXX = "XXXX"
