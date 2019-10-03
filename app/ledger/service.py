from fastapi import Depends
from starlette.requests import Request
from app.commons.service import BaseService
from app.commons.providers.dsj_client import DSJClient
from app.ledger.core.mx_ledger.processor import MxLedgerProcessors
from app.ledger.core.mx_transaction.processor import MxTransactionProcessors
from app.ledger.repository import (
    mx_ledger_repository,
    mx_transaction_repository,
    mx_scheduled_ledger_repository,
)

__all__ = [
    "create_mx_ledger_processors",
    "create_mx_transaction_processors",
    "LedgerService",
    "MxTransactionRepository",
    "MxTransactionRepositoryInterface",
    "MxLedgerRepository",
    "MxLedgerRepositoryInterface",
    "MxScheduledLedgerRepository",
    "MxScheduledLedgerRepositoryInterface",
]


MxTransactionRepositoryInterface = (
    mx_transaction_repository.MxTransactionRepositoryInterface
)
MxLedgerRepositoryInterface = mx_ledger_repository.MxLedgerRepositoryInterface
MxScheduledLedgerRepositoryInterface = (
    mx_scheduled_ledger_repository.MxScheduledLedgerRepositoryInterface
)


class LedgerService(BaseService):
    service_name = "ledger-service"
    mx_transactions: mx_transaction_repository.MxTransactionRepository
    mx_ledgers: mx_ledger_repository.MxLedgerRepository
    mx_scheduled_ledgers: mx_scheduled_ledger_repository.MxScheduledLedgerRepository

    dsj_client: DSJClient

    def __init__(self, request: Request):
        super().__init__(request)

        # paymentdb
        paymentdb = self.app_context.ledger_paymentdb
        self.mx_transactions = mx_transaction_repository.MxTransactionRepository(
            paymentdb
        )
        self.mx_ledgers = mx_ledger_repository.MxLedgerRepository(paymentdb)
        self.mx_scheduled_ledgers = mx_scheduled_ledger_repository.MxScheduledLedgerRepository(
            paymentdb
        )

        # dsj_client
        self.dsj_client = self.app_context.dsj_client


def MxTransactionRepository(
    ledger_service: LedgerService = Depends()
) -> mx_transaction_repository.MxTransactionRepositoryInterface:
    return ledger_service.mx_transactions


def MxLedgerRepository(
    ledger_service: LedgerService = Depends()
) -> mx_ledger_repository.MxLedgerRepositoryInterface:
    return ledger_service.mx_ledgers


def MxScheduledLedgerRepository(
    ledger_service: LedgerService = Depends()
) -> mx_scheduled_ledger_repository.MxScheduledLedgerRepositoryInterface:
    return ledger_service.mx_scheduled_ledgers


def DSJClientHandle(ledger_service: LedgerService = Depends()):
    return ledger_service.dsj_client


def create_mx_ledger_processors(ledger_service: LedgerService = Depends()):
    return MxLedgerProcessors(
        logger=ledger_service.log,
        mx_transaction_repo=ledger_service.mx_transactions,
        mx_ledger_repo=ledger_service.mx_ledgers,
    )


def create_mx_transaction_processors(ledger_service: LedgerService = Depends()):
    return MxTransactionProcessors(
        logger=ledger_service.log, mx_transaction_repo=ledger_service.mx_transactions
    )
