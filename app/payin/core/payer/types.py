from enum import Enum


class PayerType(str, Enum):
    """
    Enum definition of payer type. Be backward compatible with stripe_customer.owner_type in DSJ.
    """

    MARKETPLACE = "marketplace"
    DRIVE = "drive"
    MERCHANT = "merchant"
    STORE = "store"
    BUSINESS = "business"
