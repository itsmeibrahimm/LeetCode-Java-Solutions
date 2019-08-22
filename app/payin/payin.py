from fastapi import Depends

from app.commons.applications import FastAPI
from app.commons.auth.service_auth import RouteAuthorizer
from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext, set_context_for_app
from app.commons.routing import group_routers
from app.payin.api.payer.v1.api import create_payer_router
from app.payin.api.payment_method.v1.api import create_payment_method_router
from app.commons.error.errors import register_payment_exception_handler
from app.payin.api.cart_payment.v1.api import create_cart_payments_router
from app.payin.api import webhook


def create_payin_app(context: AppContext, config: AppConfig) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/payin", description="Payin service")
    set_context_for_app(app, context)

    # Init routers
    cart_payments_router = create_cart_payments_router()
    payer_router = create_payer_router()
    payment_method_router = create_payment_method_router()

    router_authorizer = RouteAuthorizer(config.PAYIN_SERVICE_ID)

    grouped_routers = group_routers(
        [payer_router, cart_payments_router, payment_method_router, webhook.v1.router]
    )

    app.include_router(grouped_routers, dependencies=[Depends(router_authorizer)])

    register_payment_exception_handler(app)

    return app
