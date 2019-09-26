from app.payin.core.cart_payment.model import CartPayment
from app.payin.core.cart_payment.types import LegacyConsumerChargeId


class CreateCartPaymentLegacyResponse(CartPayment):
    dd_charge_id: LegacyConsumerChargeId
