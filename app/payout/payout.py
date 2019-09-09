from app.commons.api.exceptions import register_payment_exception_handler
from app.commons.applications import FastAPI
from app.commons.auth.service_auth import RouteAuthorizer
from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext, set_context_for_app
from app.commons.routing import default_payment_router_builder
from app.middleware.doordash_metrics import ServiceMetricsMiddleware
from app.payout.api import account, transfer, webhook


def create_payout_v0_app(context: AppContext, config: AppConfig) -> FastAPI:
    # Declare sub app
    app_v0 = FastAPI(openapi_prefix="/payout/api/v0", description="Payout service v0")
    set_context_for_app(app_v0, context)

    # allow tracking of service-level metrics
    app_v0.add_middleware(
        ServiceMetricsMiddleware,
        app_name="payout-v0",
        host=config.STATSD_SERVER,
        config=config.PAYOUT_STATSD_CONFIG,
        additional_tags={"app": "payout-v0"},
    )

    # Mount routers
    default_payment_router_builder().add_common_dependencies(
        RouteAuthorizer(config.PAYOUT_SERVICE_ID)
    ).add_sub_routers(
        {
            "/accounts": account.v0.router,
            "/transfers": transfer.v0.router,
            "/webhook": webhook.v0.router,
        }
    ).attach_to_app(
        app_v0
    )

    register_payment_exception_handler(app_v0)

    return app_v0


def create_payout_v1_app(context: AppContext, config: AppConfig) -> FastAPI:
    # Declare sub app
    app_v1 = FastAPI(openapi_prefix="/payout/api/v1", description="Payout service v1")
    set_context_for_app(app_v1, context)

    # allow tracking of service-level metrics
    app_v1.add_middleware(
        ServiceMetricsMiddleware,
        app_name="payout-v1",
        host=config.STATSD_SERVER,
        config=config.PAYOUT_STATSD_CONFIG,
        additional_tags={"app": "payout-v1"},
    )

    # Mount routers
    default_payment_router_builder().add_sub_routers(
        {"/accounts": account.v1.router}
    ).add_common_dependencies(RouteAuthorizer(config.PAYOUT_SERVICE_ID)).attach_to_app(
        app_v1
    )

    register_payment_exception_handler(app_v1)

    return app_v1
