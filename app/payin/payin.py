import logging

from fastapi import FastAPI

from app.commons.context.app_context import AppContext, set_context_for_app
from app.payin.api.payer.v1.api import router as payer_router
from app.payin.repository.repository import PayinRepositories

logger = logging.getLogger(__name__)

payin_repositories: PayinRepositories


def create_payin_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/payin", description="Payin service")
    set_context_for_app(app, context)

    # Init data repositories
    global payin_repositories
    payin_repositories = PayinRepositories(
        _maindb=context.payin_maindb, _paymentdb=context.payin_paymentdb
    )

    app.include_router(payer_router)
    return app
