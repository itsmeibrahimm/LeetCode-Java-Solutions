from fastapi import FastAPI

from app.commons.context.app_context import AppContext, set_context_for_app
from app.payout.api.accounts_router import create_accounts_router
from app.payout.repository.maindb.payment_account import PaymentAccountRepository


def create_payout_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/payout", description="Payout service")
    set_context_for_app(app, context)

    # Init data repositories
    payment_account_repository = PaymentAccountRepository.from_context(context=context)

    # Mount api
    accounts_router = create_accounts_router(payment_account_repository)
    app.include_router(router=accounts_router, prefix="/accounts")

    return app
