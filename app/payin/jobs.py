import asyncio

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext, build_req_context
from app.payin.core.cart_payment.processor import CartPaymentInterface
from app.payin.repository.cart_payment_repo import CartPaymentRepository


async def capture_uncaptured_payment_intents(
    app_context: AppContext,
    cart_payment_repo: CartPaymentRepository,
    req_context: ReqContext = None,
):
    """
    Captures all uncaptured payment intents

    :param req_context:
    :param app_context:
    :param cart_payment_repo:
    :return:
    """
    req_context = req_context or build_req_context(app_context)

    cart_payment_interface = CartPaymentInterface(
        app_context, req_context, cart_payment_repo
    )

    uncaptured_payment_intents = (
        await cart_payment_repo.find_uncaptured_payment_intents()
    )

    coroutines = [
        cart_payment_interface.capture_payment(uncaptured_payment_intent)
        for uncaptured_payment_intent in uncaptured_payment_intents
    ]

    await asyncio.gather(*coroutines)
