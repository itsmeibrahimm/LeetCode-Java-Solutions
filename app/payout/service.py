from fastapi import Depends
from starlette.requests import Request
from app.commons.service import BaseService
from app.commons.providers.dsj_client import DSJClient
from app.payout.core.account.processor import PayoutAccountProcessors
from app.payout.repository.bankdb import payout, stripe_payout_request
from app.payout.repository.maindb import payment_account, transfer

__all__ = [
    "PayoutService",
    "PaymentAccountRepository",
    "PaymentAccountRepositoryInterface",
    "TransferRepository",
    "TransferRepositoryInterface",
    "PayoutRepository",
    "PayoutRepositoryInterface",
    "StripePayoutRequestRepository",
    "StripePayoutRequestRepositoryInterface",
]

PaymentAccountRepositoryInterface = payment_account.PaymentAccountRepositoryInterface
TransferRepositoryInterface = transfer.TransferRepositoryInterface
PayoutRepositoryInterface = payout.PayoutRepositoryInterface
StripePayoutRequestRepositoryInterface = (
    stripe_payout_request.StripePayoutRequestRepositoryInterface
)


class PayoutService(BaseService):
    service_name = "payout-service"
    payment_accounts: payment_account.PaymentAccountRepository
    transfers: transfer.TransferRepository
    payouts: payout.PayoutRepository
    stripe_payout_requests: stripe_payout_request.StripePayoutRequestRepository
    dsj_client: DSJClient

    def __init__(self, request: Request):
        super().__init__(request)

        # maindb
        maindb = self.app_context.payout_maindb
        self.payment_accounts = payment_account.PaymentAccountRepository(maindb)
        self.transfers = transfer.TransferRepository(maindb)

        # bankdb
        bankdb = self.app_context.payout_bankdb
        self.payouts = payout.PayoutRepository(bankdb)
        self.stripe_payout_requests = stripe_payout_request.StripePayoutRequestRepository(
            bankdb
        )

        # dsj_client
        self.dsj_client = self.app_context.dsj_client


def PaymentAccountRepository(
    payout_service: PayoutService = Depends()
) -> payment_account.PaymentAccountRepositoryInterface:
    return payout_service.payment_accounts


def TransferRepository(
    payout_service: PayoutService = Depends()
) -> transfer.TransferRepository:
    return payout_service.transfers


def PayoutRepository(
    payout_service: PayoutService = Depends()
) -> payout.PayoutRepositoryInterface:
    return payout_service.payouts


def StripePayoutRequestRepository(
    payout_service: PayoutService = Depends()
) -> stripe_payout_request.StripePayoutRequestRepositoryInterface:
    return payout_service.stripe_payout_requests


def DSJClientHandle(payout_service: PayoutService = Depends()):
    return payout_service.dsj_client


def create_payout_account_processors(payout_service: PayoutService = Depends()):
    return PayoutAccountProcessors(
        logger=payout_service.log, payment_account_repo=payout_service.payment_accounts
    )
