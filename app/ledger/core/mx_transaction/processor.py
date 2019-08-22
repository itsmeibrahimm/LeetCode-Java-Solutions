from datetime import datetime
from typing import Optional
from uuid import UUID

from asyncpg import DataError, UniqueViolationError, LockNotAvailableError
from fastapi import Depends
from pydantic import Json
from structlog import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.ledger.core.mx_transaction.exceptions import (
    MxTransactionCreationError,
    LedgerErrorCode,
    ledger_error_message_maps,
)
from app.ledger.core.mx_transaction.utils import to_mx_transaction
from app.ledger.repository.mx_transaction_repository import (
    MxTransactionRepository,
    InsertMxTransactionWithLedgerInput,
)
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.mx_transaction.types import (
    MxTransactionType,
    MxScheduledLedgerIntervalType,
    MxLedgerType,
)
from app.ledger.repository.mx_ledger_repository import (
    GetMxLedgerByAccountInput,
    MxLedgerRepository,
)
from app.ledger.repository.mx_scheduled_ledger_repository import (
    GetMxScheduledLedgerInput,
    MxScheduledLedgerRepository,
)


class MxTransactionProcessor:
    def __init__(
        self,
        mx_transaction_repo: MxTransactionRepository = Depends(
            MxTransactionRepository.get_repository
        ),
        mx_scheduled_ledger_repo: MxScheduledLedgerRepository = Depends(
            MxScheduledLedgerRepository.get_repository
        ),
        mx_ledger_repo: MxLedgerRepository = Depends(MxLedgerRepository.get_repository),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.mx_transaction_repo = mx_transaction_repo
        self.mx_scheduled_ledger_repo = mx_scheduled_ledger_repo
        self.mx_ledger_repo = mx_ledger_repo
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
        context: Optional[Json] = None,
        metadata: Optional[Json] = None,
        legacy_transaction_id: Optional[str] = None,
    ) -> MxTransaction:
        """
        Get or create mx_ledger and mx_scheduled_ledger and create mx_txn attached and update corresponding balance
        """
        self.log.info(
            f"[create_mx_transaction_impl] payment_account_id: {payment_account_id}, target_type: {target_type.value}"
        )

        # with given payment_account_id, routing_key and interval_type, retrieve open scheduled ledger
        get_scheduled_ledger_request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=routing_key,
            interval_type=interval_type,
        )
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
        mx_scheduled_ledger = await self.mx_scheduled_ledger_repo.get_open_mx_scheduled_ledger_for_period(
            get_scheduled_ledger_request
        )
        mx_ledger_id = mx_scheduled_ledger.ledger_id if mx_scheduled_ledger else None

        # if not found, retrieve open ledger for current payment_account
        if not mx_scheduled_ledger:
            get_mx_ledger_request = GetMxLedgerByAccountInput(
                payment_account_id=payment_account_id
            )
            mx_ledger = await self.mx_ledger_repo.get_open_ledger_for_payment_account(
                get_mx_ledger_request
            )
            mx_ledger_id = mx_ledger.id if mx_ledger else None
            # if not found, create new mx_scheduled_ledger and mx_ledger
            if not mx_ledger:
                try:
                    created_mx_txn = await self.mx_transaction_repo.create_ledger_and_insert_mx_transaction(
                        request_input, self.mx_scheduled_ledger_repo
                    )
                    return to_mx_transaction(created_mx_txn)
                except DataError as e:
                    self.log.error(
                        f"[create_ledger_and_insert_mx_transaction] Invalid input data while inserting mx transaction and creating ledger, {e}"
                    )

                    raise MxTransactionCreationError(
                        error_code=LedgerErrorCode.MX_TXN_CREATE_ERROR,
                        error_message=ledger_error_message_maps[
                            LedgerErrorCode.MX_TXN_CREATE_ERROR.value
                        ],
                        retryable=True,
                    )
                except UniqueViolationError as e:
                    self.log.warn(
                        f"[create_ledger_and_insert_mx_transaction] Retry to update ledger balance instead of insert due to unique constraints violation, {e}"
                    )
                    # retry with insert_mx_txn_and_update_ledger
                    mx_scheduled_ledger = await self.mx_scheduled_ledger_repo.get_open_mx_scheduled_ledger_for_period(
                        get_scheduled_ledger_request
                    )
                    # no exceptions should be raised from the assertion
                    assert mx_scheduled_ledger
                    mx_ledger_id = mx_scheduled_ledger.ledger_id

                except Exception as e:
                    self.log.error(
                        f"[create_ledger_and_insert_mx_transaction] Exception caught while inserting mx transaction and creating ledger, {e}"
                    )
                    raise e

        # create transaction attached and update balance with given mx_ledger_id
        assert mx_ledger_id  # no exceptions should be raised from the assertion
        created_mx_txn = await self.insert_mx_txn_and_update_ledger_balance(
            mx_ledger_id, request_input
        )
        return to_mx_transaction(created_mx_txn)

    async def insert_mx_txn_and_update_ledger_balance(
        self, ledger_id: UUID, request_input: InsertMxTransactionWithLedgerInput
    ):

        try:
            created_mx_txn = await self.mx_transaction_repo.insert_mx_transaction_and_update_ledger(
                request_input, self.mx_ledger_repo, ledger_id
            )
        except DataError as e:
            self.log.error(
                f"[insert_mx_transaction_and_update_ledger] Invalid input data while inserting mx transaction and updating ledger, {e}"
            )
            raise MxTransactionCreationError(
                error_code=LedgerErrorCode.MX_TXN_CREATE_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_TXN_CREATE_ERROR.value
                ],
                retryable=True,
            )
        except LockNotAvailableError as e:
            self.log.error(
                f"[insert_mx_transaction_and_update_ledger] Cannot obtain lock while updating ledger {ledger_id} balance {e}"
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
                f"[insert_mx_transaction_and_update_ledger] Exception caught while updating ledger {ledger_id} balance {e}"
            )
            raise e
        return created_mx_txn
