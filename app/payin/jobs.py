import asyncio
from datetime import datetime, timedelta

from app.commons import timing
from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext, build_req_context
from app.payin.core.cart_payment.model import PaymentIntent
from app.payin.core.cart_payment.processor import (
    CartPaymentProcessor,
    CartPaymentInterface,
    LegacyPaymentInterface,
)
from app.payin.core.cart_payment.types import IntentStatus
from app.payin.repository.cart_payment_repo import CartPaymentRepository

# Semaphore used to ensure there are no more than 5 concurrent coroutines being executed for capturing payment intents
capture_payment_intent_semaphore = asyncio.Semaphore(5)
resolve_capturing_payment_intent_semaphore = asyncio.Semaphore(5)


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


@timing.track_func
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
    legacy_payment_interface = LegacyPaymentInterface(
        app_context, req_context, cart_payment_repo
    )
    cart_payment_processor = CartPaymentProcessor(
        req_context.log, cart_payment_interface, legacy_payment_interface
    )

    async with capture_payment_intent_semaphore:
        return await cart_payment_processor.capture_payment(uncaptured_payment_intent)


async def resolve_capturing_payment_intents(
    app_context: AppContext,
    cart_payment_repo: CartPaymentRepository,
    req_context: ReqContext = None,
):
    """
    Payment intents that are in capturing and haven't been updated in a while likely died.
    The capturing process idempotently handles captures, so it should be fine just to re-set
    the state of these payment intents to requires_capture and let the regular cron just try
    to re-capture.

    :return:
    """
    req_context = req_context or build_req_context(app_context)

    # Look for payment intents that haven't been updated in an hour and still in capturing
    # This should be a good indication that the capturing process died
    payment_intents = await cart_payment_repo.find_payment_intents_in_capturing(
        datetime.utcnow() - timedelta(hours=1)
    )

    futures = [
        _resolve_capturing_payment_intents(cart_payment_repo, payment_intent)
        for payment_intent in payment_intents
    ]
    await asyncio.gather(*futures)


@timing.track_func
async def _resolve_capturing_payment_intents(
    cart_payment_repo: CartPaymentRepository, payment_intent: PaymentIntent
):
    async with resolve_capturing_payment_intent_semaphore:
        return await cart_payment_repo.update_payment_intent_status(
            payment_intent.id,
            new_status=IntentStatus.REQUIRES_CAPTURE.value,
            previous_status=payment_intent.status,
        )
