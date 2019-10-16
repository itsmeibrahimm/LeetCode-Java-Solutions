from structlog.stdlib import BoundLogger

from app.payout.core.transaction.processors.create_transaction import (
    CreateTransactionRequest,
    CreateTransaction,
)
from app.payout.core.transaction.processors.list_transactions import (
    ListTransactionsRequest,
    ListTransactions,
)
from app.payout.core.transaction.types import (
    TransactionListInternal,
    TransactionInternal,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface


class TransactionProcessors:
    logger: BoundLogger
    transaction_repo: TransactionRepositoryInterface

    def __init__(
        self, logger: BoundLogger, transaction_repo: TransactionRepositoryInterface
    ):
        self.logger = logger
        self.transaction_repo = transaction_repo

    async def list_transactions(
        self, request: ListTransactionsRequest
    ) -> TransactionListInternal:
        list_transactions_op = ListTransactions(
            logger=self.logger, transaction_repo=self.transaction_repo, request=request
        )
        return await list_transactions_op.execute()

    async def create_transaction(
        self, request: CreateTransactionRequest
    ) -> TransactionInternal:
        create_transactions_op = CreateTransaction(
            logger=self.logger, transaction_repo=self.transaction_repo, request=request
        )
        return await create_transactions_op.execute()
