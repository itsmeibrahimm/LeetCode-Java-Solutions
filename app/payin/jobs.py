from datetime import datetime, timedelta

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.context.req_context import build_req_context
from app.commons.jobs.pool import JobPool
from app.payin.core.cart_payment.processor import (
    CartPaymentProcessor,
    CartPaymentInterface,
    LegacyPaymentInterface,
)
from app.payin.core.cart_payment.types import IntentStatus
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository

logger = get_logger("jobs")


async def job_callback(res, err, ctx):
    if err:  # error handling
        logger.exception("Exception running job")
    else:
        logger.debug("Job successfully completed")


async def capture_uncaptured_payment_intents(
    app_context: AppContext, job_pool: JobPool
):
    """
    Captures all uncaptured payment intents

    :param app_context:
    :param job_pool:
    :return:
    """
    app_context.log.info(
        "[payment-service cron job] triggering",
        job="capture_uncaptured_payment_intents",
    )
    req_context = build_req_context(app_context)

    cart_payment_repo = CartPaymentRepository(context=app_context)
    payer_repo = PayerRepository(context=app_context)
    payment_method_repo = PaymentMethodRepository(context=app_context)

    payer_client = PayerClient(
        app_ctxt=app_context,
        log=req_context.log,
        payer_repo=payer_repo,
        stripe_async_client=req_context.stripe_async_client,
    )

    payment_method_client = PaymentMethodClient(
        payment_method_repo=payment_method_repo,
        log=req_context.log,
        app_ctxt=app_context,
        stripe_async_client=req_context.stripe_async_client,
    )

    cart_payment_interface = CartPaymentInterface(
        app_context=app_context,
        req_context=req_context,
        payment_repo=cart_payment_repo,
        payer_client=payer_client,
        payment_method_client=payment_method_client,
        stripe_async_client=req_context.stripe_async_client,
    )
    legacy_payment_interface = LegacyPaymentInterface(
        app_context=app_context,
        req_context=req_context,
        payment_repo=cart_payment_repo,
        stripe_async_client=req_context.stripe_async_client,
    )
    cart_payment_processor = CartPaymentProcessor(
        log=req_context.log,
        cart_payment_interface=cart_payment_interface,
        legacy_payment_interface=legacy_payment_interface,
    )

    uncaptured_payment_intents = cart_payment_repo.find_payment_intents_that_require_capture_before_cutoff(
        datetime.utcnow()
    )

    count: int = 0
    async for payment_intent in uncaptured_payment_intents:
        count += 1
        await job_pool.spawn(
            cart_payment_processor.capture_payment(payment_intent), cb=job_callback
        )
    app_context.log.info(
        "[payment-service cron job] triggered",
        payment_intent_count=count,
        job="capture_uncaptured_payment_intents",
    )


async def resolve_capturing_payment_intents(app_context: AppContext, job_pool: JobPool):
    """
    Payment intents that are in capturing and haven't been updated in a while likely died.
    The capturing process idempotently handles captures, so it should be fine just to re-set
    the state of these payment intents to requires_capture and let the regular cron just try
    to re-capture.

    :return:
    """
    app_context.log.info(
        "[payment-service cron job] triggering", job="resolve_capturing_payment_intents"
    )
    cart_payment_repo = CartPaymentRepository(app_context)

    # Look for payment intents that haven't been updated in an hour and still in capturing
    # This should be a good indication that the capturing process died
    cutoff = datetime.utcnow() - timedelta(hours=1)
    payment_intents = await cart_payment_repo.find_payment_intents_in_capturing(cutoff)

    for payment_intent in payment_intents:
        await job_pool.spawn(
            cart_payment_repo.update_payment_intent_status(
                payment_intent.id,
                new_status=IntentStatus.REQUIRES_CAPTURE.value,
                previous_status=payment_intent.status,
            )
        )
    app_context.log.info(
        "[payment-service cron job] triggered", job="resolve_capturing_payment_intents"
    )


async def emit_problematic_capture_count(
    app_context: AppContext,
    statsd_client: DoorStatsProxyMultiServer,
    problematic_threshold: timedelta,
):
    """
    Emits the number of problematic captures to statsd
    """
    app_context.log.info(
        "[payment-service cron job] triggering", job="emit_problematic_capture_count"
    )
    cart_payment_repo = CartPaymentRepository(app_context)
    count = await cart_payment_repo.count_payment_intents_that_require_capture(
        problematic_threshold=problematic_threshold
    )
    statsd_client.gauge("capture.problematic_count", count)
    app_context.log.info(
        "[payment-service cron job] triggered", job="emit_problematic_capture_count"
    )
