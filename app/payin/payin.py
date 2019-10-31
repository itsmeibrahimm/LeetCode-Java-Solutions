from fastapi import Depends
from app.commons.applications import FastAPI
from app.commons.auth.service_auth import ApiSecretRouteAuthorizer
from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext, set_context_for_app
from app.commons.routing import group_routers, _correlation_id_header
from app.commons.api.exceptions import register_payment_exception_handler
from app.payin.api import cart_payment, payer, payment_method, webhook, dispute
from app.middleware.doordash_metrics import ServiceMetricsMiddleware
from app.payin.api.commando_mode import commando_route_dependency


def create_payin_v0_app(context: AppContext, config: AppConfig) -> FastAPI:
    # Declare sub app
    app_v0 = FastAPI(openapi_prefix="/payin/api/v0", description="Payin Service V0")
    set_context_for_app(app_v0, context)
    # allow tracking of service-level metrics
    app_v0.add_middleware(
        ServiceMetricsMiddleware,
        application_name="payin-v0",
        host=config.STATSD_SERVER,
        config=config.PAYIN_STATSD_CONFIG,
    )
    router_authorizer = ApiSecretRouteAuthorizer(config.PAYIN_SERVICE_ID)
    auto_commando_routers = group_routers(
        [dispute.v0.router, payer.v0.router, payment_method.v0.router],
        dependencies=[Depends(commando_route_dependency)],
    )
    custom_commando_routers = group_routers([cart_payment.v0.router])
    all_routers = group_routers([auto_commando_routers, custom_commando_routers])
    app_v0.include_router(
        all_routers,
        dependencies=[Depends(router_authorizer), Depends(_correlation_id_header)],
    )
    register_payment_exception_handler(app_v0)
    return app_v0


def create_payin_v1_app(context: AppContext, config: AppConfig) -> FastAPI:
    # Declare sub app
    app_v1 = FastAPI(openapi_prefix="/payin/api/v1", description="Payin Service V1")
    set_context_for_app(app_v1, context)
    # allow tracking of service-level metrics
    app_v1.add_middleware(
        ServiceMetricsMiddleware,
        application_name="payin-v1",
        host=config.STATSD_SERVER,
        config=config.PAYIN_STATSD_CONFIG,
    )
    router_authorizer = ApiSecretRouteAuthorizer(config.PAYIN_SERVICE_ID)
    auto_commando_routers = group_routers(
        [payer.v1.router, payment_method.v1.router],
        dependencies=[Depends(commando_route_dependency)],
    )
    custom_commando_routers = group_routers([cart_payment.v1.router, webhook.v1.router])
    all_routers = group_routers([auto_commando_routers, custom_commando_routers])
    app_v1.include_router(
        all_routers,
        dependencies=[Depends(router_authorizer), Depends(_correlation_id_header)],
    )
    register_payment_exception_handler(app_v1)
    return app_v1
