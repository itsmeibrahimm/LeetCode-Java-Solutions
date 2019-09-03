from datetime import datetime
from typing import Optional

import psycopg2
from fastapi import Depends
from psycopg2._psycopg import DataError, OperationalError
from psycopg2.errorcodes import UNIQUE_VIOLATION, LOCK_NOT_AVAILABLE
from structlog.stdlib import BoundLogger
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from app.commons.context.req_context import get_logger_from_req
from app.ledger.core.exceptions import (
    MxTransactionCreationError,
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerLockError,
    MxLedgerCreationError,
    MxLedgerCreateUniqueViolationError,
)
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.types import (
    MxScheduledLedgerIntervalType,
    MxTransactionType,
    MxLedgerType,
)
from app.ledger.repository.mx_transaction_repository import (
    InsertMxTransactionWithLedgerInput,
    MxTransactionRepository,
)


class MxTransactionProcessor:
    def __init__(
        self,
        mx_transaction_repo: MxTransactionRepository = Depends(
            MxTransactionRepository.get_repository
        ),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.mx_transaction_repo = mx_transaction_repo
        self.log = log

    async def create(
        self,
        payment_account_id: str,
        target_type: MxTransactionType,
        amount: int,
        currency: str,
        idempotency_key: str,
        routing_key: datetime,
        interval_type: MxScheduledLedgerIntervalType,
        target_id: Optional[str] = None,
        context: Optional[dict] = None,
        metadata: Optional[dict] = None,
        legacy_transaction_id: Optional[str] = None,
    ) -> MxTransaction:
        """
        Get or create mx_ledger and mx_scheduled_ledger and create mx_txn attached and update corresponding balance
        """
        self.log.info(
            f"[create mx_transaction] payment_account_id: {payment_account_id}, target_type: {target_type.value}"
        )

        # with given payment_account_id, routing_key and interval_type, retrieve open scheduled ledger
        request_input = InsertMxTransactionWithLedgerInput(
            currency=currency,
            amount=amount,
            type=MxLedgerType.SCHEDULED,
            payment_account_id=payment_account_id,
            interval_type=interval_type,
            routing_key=routing_key,
            idempotency_key=idempotency_key,
            target_type=target_type,
            legacy_transaction_id=legacy_transaction_id,
            target_id=target_id,
            context=context,
            metadata=metadata,
        )

        try:
            created_mx_transaction = await self._create_mx_transaction_impl(
                request_input
            )
            return created_mx_transaction
        except RetryError as e:
            self.log.error(
                f"[create_ledger_and_insert_mx_transaction] Failed to retry locking mx_ledger, {e}"
            )
            raise MxTransactionCreationError(
                error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
                ],
                retryable=True,
            )
        except Exception as e:
            self.log.error(
                f"[create_mx_transaction] Exception caught while creating mx transaction and upserting ledgers, {e}"
            )
            raise e

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
            self.log.error(
                f"[create_mx_transaction_and_upsert_mx_ledgers] Invalid input data while creating mx transaction and "
                f"upserting ledger, {e}"
            )

            raise MxTransactionCreationError(
                error_code=LedgerErrorCode.MX_TXN_CREATE_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_TXN_CREATE_ERROR.value
                ],
                retryable=True,
            )
        except psycopg2.IntegrityError as e:
            if e.pgcode != UNIQUE_VIOLATION:
                self.log.error(
                    f"[create_ledger_and_insert_mx_transaction] IntegrityError caught while creating ledger and "
                    f"inserting mx_transaction, {e}"
                )
                raise MxLedgerCreationError(
                    error_code=LedgerErrorCode.MX_LEDGER_CREATE_INTEGRITY_ERROR,
                    error_message=ledger_error_message_maps[
                        LedgerErrorCode.MX_LEDGER_CREATE_INTEGRITY_ERROR.value
                    ],
                    retryable=True,
                )
            self.log.warn(
                f"[create_ledger_and_insert_mx_transaction] Retry to update ledger balance instead of insert "
                f"due to unique constraints violation, {e}"
            )
            # retry with insert_mx_txn_and_update_ledger due to unique constraints violation
            raise MxLedgerCreateUniqueViolationError(
                error_code=LedgerErrorCode.MX_LEDGER_CREATE_UNIQUE_VIOLATION_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_CREATE_UNIQUE_VIOLATION_ERROR.value
                ],
                retryable=True,
            )
        except OperationalError as e:
            if e.pgcode != LOCK_NOT_AVAILABLE:
                self.log.error(
                    f"[insert_mx_transaction_and_update_ledger] OperationalError caught while inserting mx_transaction "
                    f"and updating ledger, {e}"
                )
                raise MxTransactionCreationError(
                    error_code=LedgerErrorCode.MX_TXN_OPERATIONAL_ERROR,
                    error_message=ledger_error_message_maps[
                        LedgerErrorCode.MX_TXN_OPERATIONAL_ERROR.value
                    ],
                    retryable=True,
                )
            self.log.warn(
                f"[insert_mx_transaction_and_update_ledger] Cannot obtain lock while updating ledger balance {e}"
            )
            raise MxLedgerLockError(
                error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
                ],
                retryable=True,
            )
        except Exception as e:
            self.log.error(
                f"[create_mx_transaction_and_upsert_mx_ledgers] Exception caught while creating mx transaction and "
                f"upserting ledgers, {e}"
            )
            raise e
