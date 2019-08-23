from fastapi import Depends

from app.commons.applications import FastAPI
from app.commons.auth.service_auth import RouteAuthorizer
from app.commons.config.app_config import AppConfig

from app.commons.context.app_context import AppContext, set_context_for_app
from app.commons.error.errors import register_payment_exception_handler
from app.commons.routing import group_routers
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository
from app.ledger.api.mx_transaction.v1.api import create_mx_transactions_router
from app.ledger.api.mx_ledger.v1.api import create_mx_ledgers_router


mx_ledger_repository: MxLedgerRepository
mx_transaction_repository: MxTransactionRepository
mx_scheduled_ledger_repository: MxScheduledLedgerRepository


def create_ledger_app(context: AppContext, config: AppConfig) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/ledger", description="Ledger service")
    set_context_for_app(app, context)

    # Init routers
    mx_transactions_router = create_mx_transactions_router()
    mx_ledgers_router = create_mx_ledgers_router()

    route_authorizer = RouteAuthorizer(config.LEDGER_SERVICE_ID)
    grouped_routers = group_routers([mx_transactions_router, mx_ledgers_router])

    app.include_router(grouped_routers, dependencies=[Depends(route_authorizer)])

    register_payment_exception_handler(app)

    return app
