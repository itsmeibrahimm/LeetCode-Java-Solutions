from enum import Enum


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
