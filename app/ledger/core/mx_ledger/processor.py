from structlog.stdlib import BoundLogger
from app.ledger.core.mx_ledger.processors.create_mx_ledger import (
    CreateMxLedgerRequest,
    CreateMxLedger,
)
from app.ledger.core.mx_ledger.processors.process_mx_ledger import (
    ProcessMxLedgerRequest,
    ProcessMxLedger,
)
from app.ledger.core.mx_ledger.processors.submit_mx_ledger import (
    SubmitMxLedger,
    SubmitMxLedgerRequest,
)
from app.ledger.core.mx_ledger.types import MxLedgerInternal
from app.ledger.repository.mx_ledger_repository import MxLedgerRepositoryInterface
from app.ledger.repository.mx_transaction_repository import (
    MxTransactionRepositoryInterface,
)


class MxLedgerProcessors:
    logger: BoundLogger
    mx_transaction_repo: MxTransactionRepositoryInterface
    mx_ledger_repo: MxLedgerRepositoryInterface

    def __init__(
        self,
        logger: BoundLogger,
        mx_transaction_repo: MxTransactionRepositoryInterface,
        mx_ledger_repo: MxLedgerRepositoryInterface,
    ):
        self.logger = logger
        self.mx_transaction_repo = mx_transaction_repo
        self.mx_ledger_repo = mx_ledger_repo

    async def create_mx_ledger(
        self, request: CreateMxLedgerRequest
    ) -> MxLedgerInternal:
        create_mx_ledger_op = CreateMxLedger(
            logger=self.logger,
            request=request,
            mx_transaction_repo=self.mx_transaction_repo,
        )
        return await create_mx_ledger_op.execute()

    async def process_mx_ledger(
        self, request: ProcessMxLedgerRequest
    ) -> MxLedgerInternal:
        process_mx_ledger_op = ProcessMxLedger(
            logger=self.logger, request=request, mx_ledger_repo=self.mx_ledger_repo
        )
        return await process_mx_ledger_op.execute()

    async def submit_mx_ledger(
        self, request: SubmitMxLedgerRequest
    ) -> MxLedgerInternal:
        submit_mx_ledger_op = SubmitMxLedger(
            logger=self.logger,
            request=request,
            mx_ledger_repo=self.mx_ledger_repo,
            mx_transaction_repo=self.mx_transaction_repo,
        )
        return await submit_mx_ledger_op.execute()
