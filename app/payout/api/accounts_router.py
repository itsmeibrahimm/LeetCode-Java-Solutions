from fastapi import APIRouter

from app.payout.domain.payout_account.models import PayoutAccount
from app.payout.domain.payout_account.payment_account_repository import (
    PayoutAccountRepository,
)
from .models import CreatePayoutAccountRequest


def create_accounts_router(payout_accounts: PayoutAccountRepository) -> APIRouter:
    router = APIRouter()

    @router.get("/{id}")
    async def get_account(id: int):
        return await payout_accounts.get_payout_account_by_id(payment_account_id=id)

    @router.post("/")
    async def create_account(request: CreatePayoutAccountRequest):
        internal_payout_account = PayoutAccount(
            statement_descriptor=request.statement_descriptor,
            account_type=request.account_type,
            entity=request.entity,
        )
        return await payout_accounts.create_payout_account(internal_payout_account)

    return router
