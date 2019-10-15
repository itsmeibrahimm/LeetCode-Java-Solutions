from structlog.stdlib import BoundLogger

from app.payout.core.transaction.processors.list_transactions import (
    ListTransactionsRequest,
    ListTransactions,
)
from app.payout.core.transaction.types import TransactionListInternal
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
