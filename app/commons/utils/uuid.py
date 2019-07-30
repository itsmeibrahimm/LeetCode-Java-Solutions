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


def generate_object_uuid(prefix: ResourceUuidPrefix) -> str:
    """
    Generate UUID for payment object.
    :param prefix: uuid prefix
    :return: string uuid
    """
    # FIXME: for integration test now, need to revisit the algorithm of uuid generation,
    # rather than using uuid module directly
    return "{}_{}".format(prefix.value, uuid.uuid4())
