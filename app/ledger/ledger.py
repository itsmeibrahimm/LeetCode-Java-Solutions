from fastapi import FastAPI

from app.commons.context.app_context import AppContext, set_context_for_app

from app.ledger.api.mx_transaction.v1.api import router as mx_transaction_router
from app.ledger.repository.repository import LedgerRepositories

ledger_repositories: LedgerRepositories


def create_ledger_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/ledger", description="Ledger service")
    set_context_for_app(app, context)

    # Init data repositories
    global ledger_repositories
    ledger_repositories = LedgerRepositories(
        _maindb_connection=context.ledger_maindb_master,
        _paymentdb_connection=context.ledger_paymentdb_master,
    )

    app.include_router(mx_transaction_router)
    return app
