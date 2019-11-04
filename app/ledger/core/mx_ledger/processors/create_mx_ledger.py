from datetime import datetime
from typing import Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.errors import DBDataError
from app.commons.core.processor import OperationRequest, AsyncOperation
from app.ledger.core.mx_ledger.types import MxLedgerInternal
import uuid
from structlog.stdlib import BoundLogger
from app.ledger.core.data_types import InsertMxTransactionWithLedgerInput
from app.ledger.core.exceptions import LedgerErrorCode, MxLedgerCreationError
from app.ledger.core.types import MxLedgerType
from app.ledger.repository.mx_transaction_repository import (
    MxTransactionRepositoryInterface,
)


class CreateMxLedgerRequest(OperationRequest):
    currency: str
    balance: int
    payment_account_id: str
    type: str


class CreateMxLedger(AsyncOperation[CreateMxLedgerRequest, MxLedgerInternal]):
    """
    Move mx_ledger to PROCESSING and close mx_scheduled_ledger.
    """

    mx_transaction_repo: MxTransactionRepositoryInterface

    def __init__(
        self,
        request: CreateMxLedgerRequest,
        *,
        mx_transaction_repo: MxTransactionRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.mx_transaction_repo = mx_transaction_repo

    async def _execute(self) -> MxLedgerInternal:
        """
        Create a mx_ledger
        """
        try:
            if self.request.type == MxLedgerType.MICRO_DEPOSIT:
                request_input = InsertMxTransactionWithLedgerInput(
                    currency=self.request.currency,
                    amount=self.request.balance,
                    type=self.request.type,
                    payment_account_id=self.request.payment_account_id,
                    routing_key=datetime.utcnow(),
                    idempotency_key=str(uuid.uuid4()),
                    target_type=MxLedgerType.MICRO_DEPOSIT,
                )
                mx_ledger, mx_transaction = await self.mx_transaction_repo.create_ledger_and_insert_mx_transaction_caller(
                    request=request_input
                )
                return mx_ledger
            raise Exception(
                "By now only is micro-deposit supported for mx_ledger creation"
            )
        except DBDataError as e:
            self.logger.error(
                "[create_mx_ledger] Invalid input data while creating ledger", error=e
            )
            raise MxLedgerCreationError(
                error_code=LedgerErrorCode.MX_LEDGER_CREATE_ERROR, retryable=True
            )
        except Exception as e:
            self.logger.error(
                "[create_mx_ledger] Exception caught while creating mx_ledger", error=e
            )
            raise e

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, MxLedgerInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
