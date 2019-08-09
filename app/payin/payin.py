from app.commons.applications import FastAPI
from app.commons.context.app_context import AppContext, set_context_for_app
from app.payin.api.payer.v1.api import create_payer_router
from app.payin.api.payment_method.v1.api import create_payment_method_router
from app.commons.error.errors import register_payment_exception_handler
from app.payin.api.cart_payment.v1.api import create_cart_payments_router
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import PayerRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository


def create_payin_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/payin", description="Payin service")
    set_context_for_app(app, context)

    # Init routers
    cart_payments_router = create_cart_payments_router(
        CartPaymentRepository(context=context)
    )
    payer_router = create_payer_router(
        payer_repository=PayerRepository(context=context)
    )
    payment_method_router = create_payment_method_router(
        payment_method_repository=PaymentMethodRepository(context=context)
    )

    app.include_router(payer_router)
    app.include_router(cart_payments_router)
    app.include_router(payment_method_router)

    register_payment_exception_handler(app)

    return app
