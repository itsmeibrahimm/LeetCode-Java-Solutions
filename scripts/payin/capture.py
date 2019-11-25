import asyncio
from datetime import datetime, timezone
from typing import Union
from uuid import UUID

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.context.req_context import build_req_context
from app.commons.jobs.pool import JobPool
from app.payin.core.cart_payment.processor import (
    CartPaymentInterface,
    CartPaymentProcessor,
    LegacyPaymentInterface,
)
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository

__all__ = ["run_capture_one_payment_intent", "run_capture_payment_intents"]

log = get_logger("capture_scripts")


async def _capture_all_payment_intents(
    app_context: AppContext,
    job_pool: JobPool,
    latest_capture_after: datetime,
    chunk_size: int = 5,
):

    log.info(
        f"Attempting to capture payment intents with capture_after is earlier than {latest_capture_after}"
    )

    cart_payment_repo = CartPaymentRepository(context=app_context)
    payer_repo = PayerRepository(context=app_context)
    payment_method_repo = PaymentMethodRepository(context=app_context)
    req_context = build_req_context(app_context)
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

    payment_intents = cart_payment_repo.find_payment_intents_that_require_capture(
        capturable_before=latest_capture_after,
        earliest_capture_after=datetime.fromtimestamp(0).replace(tzinfo=timezone.utc),
    )

    failed_intent_ids = []
    total_intent_count = 0
    async for payment_intent in payment_intents:
        while job_pool.active_job_count >= chunk_size:
            log.info(
                f"Waiting for active jobs {job_pool.active_job_count} reduced to be lower than limit {chunk_size}"
            )
            await asyncio.sleep(0.1)

        total_intent_count += 1

        async def job_callback(res, err, ctx):
            if err:
                log.error(
                    f"Capture failed for payment_intent_id={payment_intent.id}",
                    exc_info=err[0],
                )  # err = (exec, traceback)
                failed_intent_ids.append(payment_intent.id)
            else:
                log.info(f"Capture succeeded for payment_intent_id={payment_intent.id}")

        await job_pool.spawn(
            cart_payment_processor.capture_payment(payment_intent=payment_intent),
            cb=job_callback,
        )

    # wait for all spawned capture tasks finish
    await job_pool.join()

    log.info(
        f"Capture payment intents run for total {total_intent_count} payment intents"
    )

    if failed_intent_ids:
        log.warning(f"Failed to capture these payment_intent_ids={failed_intent_ids}")


async def _capture_payment_intent(
    payment_intent_id: Union[str, UUID], app_context: AppContext
):
    if not isinstance(payment_intent_id, UUID):
        try:
            payment_intent_id = UUID(payment_intent_id)
        except ValueError:
            log.exception(f"malformed payment_intent_id={payment_intent_id}")
            return

    log.info(f"Attempt to capture payment intent id={payment_intent_id}")
    cart_payment_repo = CartPaymentRepository(context=app_context)
    payer_repo = PayerRepository(context=app_context)
    payment_method_repo = PaymentMethodRepository(context=app_context)
    req_context = build_req_context(app_context)
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

    processor = CartPaymentProcessor(
        log=req_context.log,
        cart_payment_interface=cart_payment_interface,
        legacy_payment_interface=legacy_payment_interface,
    )

    payment_intent = await cart_payment_repo.get_payment_intent_by_id(payment_intent_id)

    if payment_intent:
        log.info(f"Found payment intent={payment_intent.json()}")
        try:
            await processor.capture_payment(payment_intent)
            log.info(f"payment intent captured, id={payment_intent.id}")
        except Exception:
            log.exception(f"payment intent capture failed, id={payment_intent.id}")


def run_capture_payment_intents(
    *,
    app_context: AppContext,
    job_pool: JobPool,
    latest_capture_after: datetime,
    chunk_size: int = 5,
):
    """
    Scripts to capture all requires_capture payment intents which capture_after is earlier than latest_capture_after
    Args:
        app_context: app_context
        job_pool: aio job pool for concurrency
        latest_capture_after: payment intent's capture_after need to be earlier than this threshold
            in order to be captured
        chunk_size: chunk size to control maximum concurrency to speed up capture.
            !!DO NOT!! set this too high as roughly chunk_size / 2 = stripe call rps

    Returns: None

    """

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        _capture_all_payment_intents(
            app_context=app_context,
            job_pool=job_pool,
            latest_capture_after=latest_capture_after,
            chunk_size=chunk_size,
        )
    )


def run_capture_one_payment_intent(
    *, payment_intent_id: Union[str, UUID], app_context: AppContext
):
    """
    Scripts to capture one single payment intent
    Args:
        payment_intent_id: payment_intent_id
        app_context: app_context

    Returns: None

    """

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        _capture_payment_intent(
            payment_intent_id=payment_intent_id, app_context=app_context
        )
    )
