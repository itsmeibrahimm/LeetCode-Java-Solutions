from app.commons.applications import FastAPI

from app.commons.context.app_context import AppContext, set_context_for_app
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository
from app.ledger.api.mx_transaction.v1.api import create_mx_transactions_router

mx_ledger_repository: MxLedgerRepository
mx_transaction_repository: MxTransactionRepository
mx_scheduled_ledger_repository: MxScheduledLedgerRepository


def create_ledger_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/ledger", description="Ledger service")
    set_context_for_app(app, context)

    # Init routers
    mx_transactions_router = create_mx_transactions_router(
        MxTransactionRepository(context=context)
    )

    app.include_router(mx_transactions_router)

    return app
