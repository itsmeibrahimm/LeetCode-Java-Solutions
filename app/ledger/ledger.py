from fastapi import Depends

from app.commons.applications import FastAPI
from app.commons.auth.service_auth import ApiSecretRouteAuthorizer
from app.commons.config.app_config import AppConfig

from app.commons.context.app_context import AppContext, set_context_for_app
from app.commons.api.exceptions import register_base_payment_exception_handler
from app.commons.routing import group_routers
from app.ledger.api import mx_transaction, mx_ledger
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository
from app.middleware.doordash_metrics import ServiceMetricsMiddleware


mx_ledger_repository: MxLedgerRepository
mx_transaction_repository: MxTransactionRepository
mx_scheduled_ledger_repository: MxScheduledLedgerRepository


def create_ledger_app(context: AppContext, config: AppConfig) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/ledger", description="Ledger service")
    set_context_for_app(app, context)

    # allow tracking of service-level metrics
    app.add_middleware(
        ServiceMetricsMiddleware,
        application_name="ledger-v1",
        host=config.STATSD_SERVER,
        config=config.LEDGER_STATSD_CONFIG,
    )

    route_authorizer = ApiSecretRouteAuthorizer(config.LEDGER_SERVICE_ID)
    grouped_routers = group_routers([mx_transaction.v1.router, mx_ledger.v1.router])

    app.include_router(grouped_routers, dependencies=[Depends(route_authorizer)])

    register_base_payment_exception_handler(app)

    return app
