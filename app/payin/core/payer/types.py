from enum import Enum


class PayerType(str, Enum):
    """
    Enum definition of payer type. Be backword compatible with stripe_customer.owner_type in DSJ.
    """

    MARKETPLACE = "marketplace"
    DRIVE = "drive"
    MERCHANT = "marchant"
    STORE = "store"
    BUSINESS = "business"
