from typing import Optional

from app.payin.core.payment_method.model import PaymentMethod
from app.payin.core.types import LegacyPaymentInfo


async def create_payment_method_impl(
    payer_id: Optional[str],
    payment_gateway: str,
    token: str,
    legacy_payment_info: Optional[LegacyPaymentInfo],
) -> PaymentMethod:
    ...


async def get_payment_method_impl(
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_object_type: str = None,
) -> PaymentMethod:
    ...


async def list_payment_methods_impl(
    payer_id: str, payer_id_type: str = None
) -> PaymentMethod:
    ...


async def delete_payment_method_impl(
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_object_type: str = None,
) -> PaymentMethod:
    ...
