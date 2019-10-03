from structlog.stdlib import BoundLogger
from app.ledger.core.mx_transaction.processors.create_mx_transaction import (
    CreateMxTransactionRequest,
    CreateMxTransaction,
)
from app.ledger.core.mx_transaction.types import MxTransactionInternal
from app.ledger.repository.mx_transaction_repository import (
    MxTransactionRepositoryInterface,
)


class MxTransactionProcessors:
    logger: BoundLogger
    mx_transaction_repo: MxTransactionRepositoryInterface

    def __init__(
        self, logger: BoundLogger, mx_transaction_repo: MxTransactionRepositoryInterface
    ):
        self.logger = logger
        self.mx_transaction_repo = mx_transaction_repo

    async def create_mx_transaction(
        self, request: CreateMxTransactionRequest
    ) -> MxTransactionInternal:
        create_mx_transaction_op = CreateMxTransaction(
            logger=self.logger,
            request=request,
            mx_transaction_repo=self.mx_transaction_repo,
        )
        return await create_mx_transaction_op.execute()
