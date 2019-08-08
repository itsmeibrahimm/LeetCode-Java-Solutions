from app.commons.applications import FastAPI

from app.commons.context.app_context import AppContext, set_context_for_app
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository

mx_ledger_repository: MxLedgerRepository
mx_transaction_repository: MxTransactionRepository
mx_scheduled_ledger_repository: MxScheduledLedgerRepository


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

    global mx_scheduled_ledger_repository
    mx_scheduled_ledger_repository = MxScheduledLedgerRepository(context=context)

    return app
