from app.commons.applications import FastAPI

from app.commons.context.app_context import AppContext, set_context_for_app
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository
from app.payin.api.payer.v1.api import router as mx_transaction_router

mx_ledger_repository: MxLedgerRepository
mx_transaction_repository: MxTransactionRepository


def create_ledger_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/ledger", description="Ledger service")
    set_context_for_app(app, context)

    # TODO remove use of global variable
    # Init data repositories
    global mx_ledger_repository
    mx_ledger_repository = MxLedgerRepository(context=context)

    global mx_transaction_repository
    mx_transaction_repository = MxTransactionRepository(context=context)

    app.include_router(mx_transaction_router)

    return app
