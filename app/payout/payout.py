from app.commons.applications import FastAPI
from app.commons.context.app_context import AppContext, set_context_for_app
from app.commons.error.errors import register_payment_exception_handler
from app.payout.api import account, transfer, webhook


def create_payout_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app_v0 = FastAPI(openapi_prefix="/payout/api/v0", description="Payout service")
    set_context_for_app(app_v0, context)

    # Mount routers
    app_v0.include_router(router=account.v0.router, prefix="/accounts")
    app_v0.include_router(router=transfer.v0.router, prefix="/transfers")
    app_v0.include_router(router=webhook.v0.router, prefix="/webhook")

    register_payment_exception_handler(app_v0)

    return app_v0
