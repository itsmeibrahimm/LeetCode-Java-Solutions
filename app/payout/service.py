from fastapi import Depends
from starlette.requests import Request
from app.commons.service import BaseService
from app.payout.repository.maindb import payment_account, transfer

__all__ = [
    "PayoutService",
    "PaymentAccountRepository",
    "PaymentAccountRepositoryInterface",
    "TransferRepository",
    "TransferRepositoryInterface",
]

PaymentAccountRepositoryInterface = payment_account.PaymentAccountRepositoryInterface
TransferRepositoryInterface = transfer.TransferRepositoryInterface


class PayoutService(BaseService):
    service_name = "payout-service"
    payment_accounts: payment_account.PaymentAccountRepository
    transfers: transfer.TransferRepository

    def __init__(self, request: Request):
        super().__init__(request)

        # maindb
        maindb = self.app_context.payout_maindb
        self.payment_accounts = payment_account.PaymentAccountRepository(maindb)
        self.transfers = transfer.TransferRepository(maindb)


def PaymentAccountRepository(
    payout_service: PayoutService = Depends()
) -> payment_account.PaymentAccountRepositoryInterface:
    return payout_service.payment_accounts


def TransferRepository(
    payout_service: PayoutService = Depends()
) -> transfer.TransferRepository:
    return payout_service.transfers
