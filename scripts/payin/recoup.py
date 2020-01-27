import asyncio
from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payin.core.cart_payment.commando_mode_processor import CommandoProcessor
from app.payin.core.cart_payment.cart_payment_client import CartPaymentInterface
from app.payin.core.cart_payment.legacy_cart_payment_client import (
    LegacyPaymentInterface,
)
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository

__all__ = ["run_recoup"]


def _build_commando_processor(app_context: AppContext) -> CommandoProcessor:
    req_context = build_req_context(app_context)
    payment_method_repo = PaymentMethodRepository(context=app_context)
    payer_repo = PayerRepository(context=app_context)
    cart_payment_repo = CartPaymentRepository(context=app_context)

    payment_method_client = PaymentMethodClient(
        payment_method_repo=payment_method_repo,
        log=req_context.log,
        app_ctxt=app_context,
        stripe_async_client=req_context.stripe_async_client,
    )

    payer_client = PayerClient(
        payer_repo=payer_repo,
        log=req_context.log,
        app_ctxt=app_context,
        stripe_async_client=req_context.stripe_async_client,
    )

    cart_payment_interface = CartPaymentInterface(
        app_context=app_context,
        req_context=req_context,
        payment_repo=cart_payment_repo,
        payment_method_client=payment_method_client,
        payer_client=payer_client,
        stripe_async_client=req_context.stripe_async_client,
    )

    legacy_payment_interface = LegacyPaymentInterface(
        app_context=app_context,
        req_context=req_context,
        payment_repo=cart_payment_repo,
        stripe_async_client=req_context.stripe_async_client,
    )

    commando_processor = CommandoProcessor(
        log=req_context.log,
        cart_payment_interface=cart_payment_interface,
        legacy_payment_interface=legacy_payment_interface,
        cart_payment_repo=cart_payment_repo,
    )

    return commando_processor


async def _recoup(app_context: AppContext):
    commando_processor = _build_commando_processor(app_context)
    await commando_processor.recoup(limit=10000, chunk_size=100)


def run_recoup(app_context: AppContext):
    """
    Recoup all payment intents that are created under stripe commando mode
    Args:
        app_context: app_context

    Returns: None

    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_recoup(app_context))
