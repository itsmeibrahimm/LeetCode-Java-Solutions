from app.commons.applications import FastAPI

from app.commons.context.app_context import AppContext, set_context_for_app
from app.payout.api.account.v0.api import create_account_v0_router
from app.payout.api.transfer.v0.api import create_transfer_v0_router
from app.payout.api.webhook.v0.api import webhook_v0_router
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.transfer import TransferRepository


def create_payout_app(context: AppContext) -> FastAPI:
    # Declare sub app
    app = FastAPI(openapi_prefix="/payout", description="Payout service")
    set_context_for_app(app, context)

    payment_account_repo = PaymentAccountRepository.from_context(context)
    transfer_repo = TransferRepository.from_context(context)

    # Mount routers
    app.include_router(
        router=create_account_v0_router(payment_account_repo=payment_account_repo),
        prefix="/api/v0/account",
    )
    app.include_router(
        router=create_transfer_v0_router(transfer_repo=transfer_repo),
        prefix="/api/v0/transfer",
    )
    app.include_router(
        router=webhook_v0_router(transfer_repo=transfer_repo), prefix="/api/v0/webhook"
    )

    return app
