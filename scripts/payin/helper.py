from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
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


def get_cart_payment_processor(app_context: AppContext):
    payer_repo = PayerRepository(context=app_context)
    payment_method_repo = PaymentMethodRepository(context=app_context)
    cart_payment_repo = CartPaymentRepository(context=app_context)
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

    return CartPaymentProcessor(
        log=req_context.log,
        cart_payment_interface=cart_payment_interface,
        legacy_payment_interface=legacy_payment_interface,
    )


def get_cart_payment_repo(cart_payment_processor: CartPaymentProcessor):
    return cart_payment_processor.cart_payment_interface.payment_repo


def get_cart_payment_interface(cart_payment_processor: CartPaymentProcessor):
    return cart_payment_processor.cart_payment_interface
