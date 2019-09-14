from app.payin.core.cart_payment.model import CartPayment


class CreateCartPaymentLegacyResponse(CartPayment):
    dd_charge_id: int
