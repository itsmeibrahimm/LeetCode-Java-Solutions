import logging

from fastapi import FastAPI

from app.commons.context.app_context import AppContext, set_context_for_app
from app.payin.api.payer.v1.api import router as payer_router
from app.payin.repository.payer_repo import PayerRepository

logger = logging.getLogger(__name__)

payer_repository: PayerRepository


def create_payin_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/payin", description="Payin service")
    set_context_for_app(app, context)

    # Init data repositories
    global payer_repository
    payer_repository = PayerRepository(context=context)

    app.include_router(payer_router)
    return app
