from fastapi import Depends

from app.commons.applications import FastAPI
from app.commons.auth.service_auth import RouteAuthorizer
from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext, set_context_for_app
from app.commons.routing import group_routers
from app.commons.error.errors import register_payment_exception_handler
from app.payin.api import cart_payment, payer, payment_method, webhook, dispute
from app.middleware.doordash_metrics import ServiceMetricsMiddleware


def create_payin_app(context: AppContext, config: AppConfig) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/payin", description="Payin service")
    set_context_for_app(app, context)

    # allow tracking of service-level metrics
    app.add_middleware(
        ServiceMetricsMiddleware,
        app_name="payin-v1",
        host=config.STATSD_SERVER,
        config=config.PAYIN_STATSD_CONFIG,
        additional_tags={"app": "payin-v1"},
    )

    router_authorizer = RouteAuthorizer(config.PAYIN_SERVICE_ID)

    grouped_routers = group_routers(
        [
            payer.v1.router,
            cart_payment.v1.router,
            payment_method.v1.router,
            webhook.v1.router,
            dispute.v1.router,
        ]
    )

    app.include_router(grouped_routers, dependencies=[Depends(router_authorizer)])

    register_payment_exception_handler(app)

    return app
