import asyncio
from datetime import datetime

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext, build_req_context
from app.payin.core.cart_payment.processor import CartPaymentInterface
from app.payin.repository.cart_payment_repo import CartPaymentRepository

# Semaphore used to ensure there are no more than 5 concurrent coroutines being executed for capturing payment intents
capture_payment_intent_semaphore = asyncio.Semaphore(5)


# Semaphore used to ensure there are no more than 5 concurrent coroutines being executed for capturing payment intents
capture_payment_intent_semaphore = asyncio.Semaphore(5)


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

    uncaptured_payment_intents = await cart_payment_repo.find_payment_intents_that_require_capture(
        datetime.utcnow()
    )

    coroutines = [
        _capture_payment_intent(
            app_context, req_context, cart_payment_repo, uncaptured_payment_intent
        )
        for uncaptured_payment_intent in uncaptured_payment_intents
    ]

    await asyncio.gather(*coroutines)


async def _capture_payment_intent(
    app_context, req_context, cart_payment_repo, uncaptured_payment_intent
):
    """
    Wrapper around payment intent that ensures there are no more than N concurrent payment intents being captured

    :param app_context:
    :param req_context:
    :param cart_payment_repo:
    :param uncaptured_payment_intent:
    :return:
    """
    cart_payment_interface = CartPaymentInterface(
        app_context, req_context, cart_payment_repo
    )

    async with capture_payment_intent_semaphore:
        return await cart_payment_interface.capture_payment(uncaptured_payment_intent)
