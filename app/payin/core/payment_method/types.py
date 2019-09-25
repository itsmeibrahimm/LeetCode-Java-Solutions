from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.commons.types import CountryCode
from app.payin.core.payer.types import PayerType


class WalletType(str, Enum):
    """
    Enum definition of payment method wallet type. Be backward compatible with maindb_stripe_card.tokenization_method in DSJ.
    See stripe reference for more information: https://stripe.com/docs/api/payment_methods/object?lang=curl#payment_method_object-card-wallet-type
    """

    GOOGLE_PAY = "google_pay"
    APPLE_PAY = "apple_pay"


class SortKey(str, Enum):
    """
    Enum definition of sorting method of payment method list.
    """

    CREATED_AT = "created_at"


class LegacyPaymentMethodInfo(BaseModel):
    country: CountryCode
    stripe_customer_id: str
    payer_type: PayerType
    dd_consumer_id: Optional[
        str
    ]  # required if PayerType is "marketplace" in order to populate MainDB.stripe_card.consumer_id
    dd_stripe_customer_id: Optional[
        str
    ]  # required if PayerType is not "marketplace" in order to populate MainDB.stripe_card.stripe_customer_id
