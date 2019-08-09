from app.commons.applications import FastAPI
from app.commons.context.app_context import AppContext, set_context_for_app
from app.commons.error.errors import register_payment_exception_handler
from app.payout.api.account.v0.api import create_account_v0_router
from app.payout.api.transfer.v0.api import create_transfer_v0_router
from app.payout.api.webhook.v0.api import webhook_v0_router
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.transfer import TransferRepository


def create_payout_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/payout/api/v0", description="Payout service")
    set_context_for_app(app, context)

    payment_account_repo = PaymentAccountRepository(database=context.payout_maindb)
    transfer_repo = TransferRepository(database=context.payout_maindb)

    # Mount routers
    app.include_router(
        router=create_account_v0_router(payment_account_repo=payment_account_repo),
        prefix="/accounts",
    )
    app.include_router(
        router=create_transfer_v0_router(transfer_repo=transfer_repo),
        prefix="/transfers",
    )
    app.include_router(
        router=webhook_v0_router(transfer_repo=transfer_repo), prefix="/webhook"
    )

    register_payment_exception_handler(app)

    return app
