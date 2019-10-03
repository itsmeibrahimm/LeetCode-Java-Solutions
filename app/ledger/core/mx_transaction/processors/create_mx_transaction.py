from datetime import datetime
from typing import Union, Optional

import psycopg2
from psycopg2.errorcodes import UNIQUE_VIOLATION, LOCK_NOT_AVAILABLE
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import OperationRequest, AsyncOperation
from psycopg2._psycopg import DataError, OperationalError
from structlog.stdlib import BoundLogger
from app.ledger.core.data_types import InsertMxTransactionWithLedgerInput
from app.ledger.core.exceptions import (
    LedgerErrorCode,
    MxLedgerCreationError,
    MxTransactionCreationError,
    MxLedgerCreateUniqueViolationError,
    MxLedgerLockError,
)
from app.ledger.core.mx_transaction.types import MxTransactionInternal
from app.ledger.core.types import (
    MxLedgerType,
    MxTransactionType,
    MxScheduledLedgerIntervalType,
)
from app.ledger.repository.mx_transaction_repository import (
    MxTransactionRepositoryInterface,
)


class CreateMxTransactionRequest(OperationRequest):
    payment_account_id: str
    target_type: MxTransactionType
    amount: int
    currency: str
    idempotency_key: str
    routing_key: datetime
    interval_type: MxScheduledLedgerIntervalType
    target_id: Optional[str] = None
    context: Optional[dict] = None
    metadata: Optional[dict] = None
    legacy_transaction_id: Optional[str] = None


class CreateMxTransaction(
    AsyncOperation[CreateMxTransactionRequest, MxTransactionInternal]
):
    mx_transaction_repo: MxTransactionRepositoryInterface

    def __init__(
        self,
        request: CreateMxTransactionRequest,
        *,
        mx_transaction_repo: MxTransactionRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.mx_transaction_repo = mx_transaction_repo

    async def _execute(self) -> MxTransactionInternal:
        """
        Get or create mx_ledger and mx_scheduled_ledger and create mx_txn attached and update corresponding balance
        """
        self.logger.info(
            "[create mx_transaction] Creating mx_transaction.",
            payment_account_id=self.request.payment_account_id,
            target_type=self.request.target_type.value,
        )

        # with given payment_account_id, routing_key and interval_type, retrieve open scheduled ledger
        request_input = InsertMxTransactionWithLedgerInput(
            currency=self.request.currency,
            amount=self.request.amount,
            type=MxLedgerType.SCHEDULED,
            payment_account_id=self.request.payment_account_id,
            interval_type=self.request.interval_type,
            routing_key=self.request.routing_key,
            idempotency_key=self.request.idempotency_key,
            target_type=self.request.target_type,
            legacy_transaction_id=self.request.legacy_transaction_id,
            target_id=self.request.target_id,
            context=self.request.context,
            metadata=self.request.metadata,
        )

        try:
            created_mx_transaction = await self._create_mx_transaction_impl(
                request_input
            )
            return created_mx_transaction
        except RetryError as e:
            self.logger.error(
                "[create_ledger_and_insert_mx_transaction] Failed to retry creating mx_transaction",
                error=e,
            )
            raise MxTransactionCreationError(
                error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                retryable=True,
            )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, MxTransactionInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION

    @retry(
        # retry due to MX_LEDGER_CREATE_UNIQUE_VIOLATION_ERROR or MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR
        retry=(
            retry_if_exception_type(MxLedgerCreateUniqueViolationError)
            | retry_if_exception_type(MxLedgerLockError)
        ),
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.3),
    )
    async def _create_mx_transaction_impl(
        self, request_input: InsertMxTransactionWithLedgerInput
    ):
        try:
            mx_transaction = await self.mx_transaction_repo.create_mx_transaction_and_upsert_mx_ledgers_caller(
                request_input
            )
            return mx_transaction
        except DataError as e:
            self.logger.error(
                "[create_mx_transaction_and_upsert_mx_ledgers] Invalid input data while creating mx transaction and upserting ledger",
                error=e,
            )

            raise MxTransactionCreationError(
                error_code=LedgerErrorCode.MX_TXN_CREATE_ERROR, retryable=True
            )
        except psycopg2.IntegrityError as e:
            if e.pgcode != UNIQUE_VIOLATION:
                self.logger.error(
                    "[create_ledger_and_insert_mx_transaction] IntegrityError caught while creating ledger and inserting mx_transaction",
                    error=e,
                )
                raise MxLedgerCreationError(
                    error_code=LedgerErrorCode.MX_LEDGER_CREATE_INTEGRITY_ERROR,
                    retryable=True,
                )
            self.logger.warn(
                "[create_ledger_and_insert_mx_transaction] Retry to update ledger balance instead of insert due to unique constraints violation",
                error=e,
            )
            # retry with insert_mx_txn_and_update_ledger due to unique constraints violation
            raise MxLedgerCreateUniqueViolationError(
                error_code=LedgerErrorCode.MX_LEDGER_CREATE_UNIQUE_VIOLATION_ERROR,
                retryable=True,
            )
        except OperationalError as e:
            if e.pgcode != LOCK_NOT_AVAILABLE:
                self.logger.error(
                    "[insert_mx_transaction_and_update_ledger] OperationalError caught while inserting mx_transaction and updating ledger",
                    error=e,
                )
                raise MxTransactionCreationError(
                    error_code=LedgerErrorCode.MX_TXN_OPERATIONAL_ERROR, retryable=True
                )
            self.logger.warn(
                "[insert_mx_transaction_and_update_ledger] Cannot obtain lock while updating ledger balance",
                error=e,
            )
            raise MxLedgerLockError(
                error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                retryable=True,
            )
