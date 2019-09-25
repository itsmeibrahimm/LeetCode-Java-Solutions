from enum import Enum

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
    payer_type: PayerType
