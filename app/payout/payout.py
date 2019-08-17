from fastapi import Depends

from app.commons.applications import FastAPI
from app.commons.auth.service_auth import RouteAuthorizer
from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext, set_context_for_app
from app.commons.error.errors import register_payment_exception_handler
from app.commons.routing import group_routers_with_path_prefix
from app.payout.api import account, transfer, webhook


def create_payout_app(context: AppContext, config: AppConfig) -> FastAPI:
    # Declare sub app
    app_v0 = FastAPI(openapi_prefix="/payout/api/v0", description="Payout service")
    set_context_for_app(app_v0, context)

    # Mount routers
    route_authorizer = RouteAuthorizer(config.PAYOUT_SERVICE_ID)
    grouped_routers = group_routers_with_path_prefix(
        {
            "/accounts": account.v0.router,
            "/transfers": transfer.v0.router,
            "/webhook": webhook.v0.router,
        }
    )

    app_v0.include_router(grouped_routers, dependencies=[Depends(route_authorizer)])

    register_payment_exception_handler(app_v0)

    return app_v0
