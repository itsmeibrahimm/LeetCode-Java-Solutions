from fastapi import FastAPI

from app.commons.context.app_context import AppContext

from app.payout.api.accounts_router import create_accounts_router
from app.payout.domain.repository import PayoutRepositories


def create_payout_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/payout", description="Payout service")

    # Init data repositories
    payout_repositories = PayoutRepositories(
        _maindb_connection=context.payout_maindb_master,
        _bankdb_connection=context.payout_bankdb_master,
    )

    # Mount api
    accounts_router = create_accounts_router(payout_repositories)
    app.include_router(router=accounts_router, prefix="/accounts")

    return app
