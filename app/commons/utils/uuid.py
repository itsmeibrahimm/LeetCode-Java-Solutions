import uuid
from enum import Enum


class ResourceUuidPrefix(str, Enum):
    PAYER = "pyr"
    PGP_CUSTOMER = "pgcu"
    PGP_PAYMENT_METHOD = "pgpm"
    CART_PAYMENT = "cpm"
    PAYMENT_INTENT = "pit"
    PGP_PAYMENT_INTENT = "pgpi"
    CHARGE = "cha"
    PGP_CHARGE = "pgc"
    REFUND = "ref"
    PGP_REFUND = "pgre"
    PGP_DISPUTE = "pgdp"
    STRIPE_CUSTOMER = "cus"
    MX_TRANSACTION = "mxtxn"
    MX_LEDGER = "mxl"


def generate_object_uuid() -> uuid.UUID:
    """
    Generate UUID for payment object.
    :return: string uuid
    """
    # FIXME: for integration test now, need to revisit the algorithm of uuid generation,
    # rather than using uuid module directly
    return uuid.uuid4()
