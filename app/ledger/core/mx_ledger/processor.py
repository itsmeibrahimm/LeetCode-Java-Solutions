import uuid
from datetime import datetime

from fastapi import Depends
from psycopg2._psycopg import DataError, OperationalError, IntegrityError
from psycopg2.errorcodes import LOCK_NOT_AVAILABLE, UNIQUE_VIOLATION
from structlog.stdlib import BoundLogger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
    RetryError,
)

from app.commons.context.req_context import get_logger_from_req
from app.ledger.core.data_types import (
    ProcessMxLedgerInput,
    GetMxLedgerByIdInput,
    UpdatePaidMxLedgerInput,
    RolloverNegativeLedgerInput,
    ProcessMxLedgerOutput,
    InsertMxTransactionWithLedgerInput,
)
from app.ledger.core.exceptions import (
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerProcessError,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
    MxLedgerLockError,
    MxLedgerSubmissionError,
    MxLedgerCreateUniqueViolationError,
    MxLedgerCreationError,
)
from app.ledger.core.mx_ledger.model import MxLedger
from app.ledger.core.types import MxLedgerStateType, MxLedgerType
from app.ledger.core.utils import to_mx_ledger
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository


class MxLedgerProcessor:
    def __init__(
        self,
        mx_transaction_repo: MxTransactionRepository = Depends(
            MxTransactionRepository.get_repository
        ),
        mx_ledger_repo: MxLedgerRepository = Depends(MxLedgerRepository.get_repository),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.mx_transaction_repo = mx_transaction_repo
        self.mx_ledger_repo = mx_ledger_repo
        self.log = log

    async def process(self, mx_ledger_id: uuid.UUID) -> MxLedger:
        """
        Move mx_ledger to PROCESSING and close mx_scheduled_ledger.
        """
        # check whether the given ledger exists or not
        retrieve_ledger_request = GetMxLedgerByIdInput(id=mx_ledger_id)
        retrieved_ledger = await self.mx_ledger_repo.get_ledger_by_id(
            retrieve_ledger_request
        )
        if not retrieved_ledger:
            raise MxLedgerReadError(
                error_code=LedgerErrorCode.MX_LEDGER_NOT_FOUND,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_NOT_FOUND.value
                ],
                retryable=False,
            )
        # mx_ledger state needs to be OPEN in order to be processed, otherwise raise exception
        if not retrieved_ledger.state == MxLedgerStateType.OPEN:
            raise MxLedgerInvalidProcessStateError(
                error_code=LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE.value
                ],
                retryable=False,
            )
        # process mx_ledger and close scheduled_ledger
        try:
            mx_ledger = await self.process_ledger_and_scheduled_ledger(mx_ledger_id)
            return to_mx_ledger(mx_ledger)
        except RetryError as e:
            self.log.error(
                f"[process mx_ledger] Failed to retry locking mx_ledger {mx_ledger_id}, {e}"
            )
            raise MxLedgerProcessError(
                error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
                ],
                retryable=True,
            )

    @retry(
        retry=retry_if_exception_type(MxLedgerLockError),
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.3),
    )
    async def process_ledger_and_scheduled_ledger(self, mx_ledger_id: uuid.UUID):
        process_mx_ledger_request = ProcessMxLedgerInput(id=mx_ledger_id)
        try:
            mx_ledger = await self.mx_ledger_repo.move_ledger_state_to_processing_and_close_schedule_ledger(
                process_mx_ledger_request
            )
            return to_mx_ledger(mx_ledger)
        except DataError as e:
            self.log.error(
                f"[process_ledger_and_scheduled_ledger] Invalid input data while processing ledger {mx_ledger_id}, {e}"
            )
            raise MxLedgerProcessError(
                error_code=LedgerErrorCode.MX_LEDGER_PROCESS_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_PROCESS_ERROR.value
                ],
                retryable=True,
            )
        except OperationalError as e:
            if e.pgcode != LOCK_NOT_AVAILABLE:
                self.log.error(
                    f"[process_ledger_and_scheduled_ledger] OperationalError caught while processing ledger {mx_ledger_id}, {e}"
                )
                raise MxLedgerProcessError(
                    error_code=LedgerErrorCode.MX_TXN_OPERATIONAL_ERROR,
                    error_message=ledger_error_message_maps[
                        LedgerErrorCode.MX_TXN_OPERATIONAL_ERROR.value
                    ],
                    retryable=True,
                )
            self.log.warn(
                f"[process_ledger_and_scheduled_ledger] Cannot obtain lock while updating ledger {mx_ledger_id}, {e}"
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
                f"[process_ledger_and_scheduled_ledger] Exception caught while processing ledger, {e}"
            )
            raise e

    async def submit(self, mx_ledger_id: uuid.UUID) -> MxLedger:
        """
        Submit mx_ledger to Payout Service and handle negative balance rollover if exists.
        """
        # check whether the given ledger exists or not
        retrieve_ledger_request = GetMxLedgerByIdInput(id=mx_ledger_id)
        retrieved_ledger = await self.mx_ledger_repo.get_ledger_by_id(
            retrieve_ledger_request
        )
        if not retrieved_ledger:
            raise MxLedgerReadError(
                error_code=LedgerErrorCode.MX_LEDGER_NOT_FOUND,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_NOT_FOUND.value
                ],
                retryable=False,
            )

        # mx_ledger state needs to be PROCESSING in order to be submitted, otherwise raise exception
        if not retrieved_ledger.state == MxLedgerStateType.PROCESSING:
            raise MxLedgerInvalidProcessStateError(
                error_code=LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE.value
                ],
                retryable=False,
            )

        if retrieved_ledger.balance > 0:
            # todo: call Payout Service and update status
            # after submitted to payout service, update ledger state to SUBMITTED
            submit_ledger_request = ProcessMxLedgerInput(id=mx_ledger_id)
            try:
                mx_ledger = await self.mx_ledger_repo.move_ledger_state_to_submitted(
                    submit_ledger_request
                )
            except DataError as e:
                self.log.error(
                    f"[submit mx_ledger] Invalid input data while submitting ledger {mx_ledger_id}, {e}"
                )
                raise MxLedgerSubmissionError(
                    error_code=LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR,
                    error_message=ledger_error_message_maps[
                        LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR.value
                    ],
                    retryable=True,
                )
            except Exception as e:
                raise e
            return to_mx_ledger(mx_ledger)
        elif retrieved_ledger.balance == 0:
            paid_ledger_request = UpdatePaidMxLedgerInput(
                id=mx_ledger_id, amount_paid=0
            )
            try:
                mx_ledger = await self.mx_ledger_repo.move_ledger_state_to_paid(
                    paid_ledger_request
                )
                return to_mx_ledger(mx_ledger)
            except DataError as e:
                self.log.error(
                    f"[submit mx_ledger] Invalid input data while submitting ledger {mx_ledger_id}, {e}"
                )
                raise MxLedgerSubmissionError(
                    error_code=LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR,
                    error_message=ledger_error_message_maps[
                        LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR.value
                    ],
                    retryable=True,
                )
            except Exception as e:
                raise e

        else:
            # rollover negative balance mx_ledger
            try:
                mx_ledger = await self._rollover_negative_balanced_ledger_impl(
                    mx_ledger_id
                )
                return to_mx_ledger(mx_ledger)
            except RetryError as e:
                self.log.error(
                    f"[submit mx_ledger] Failed to retry rolling over mx_ledger {mx_ledger_id}, {e}"
                )
                raise MxLedgerSubmissionError(
                    error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                    error_message=ledger_error_message_maps[
                        LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
                    ],
                    retryable=True,
                )
            except Exception as e:
                raise e

    @retry(
        retry=(
            retry_if_exception_type(MxLedgerCreateUniqueViolationError)
            | retry_if_exception_type(MxLedgerLockError)
        ),
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.3),
    )
    async def _rollover_negative_balanced_ledger_impl(
        self, mx_ledger_id: uuid.UUID
    ) -> ProcessMxLedgerOutput:
        rollover_negative_ledger_request = RolloverNegativeLedgerInput(id=mx_ledger_id)
        try:
            rolled_mx_ledger = await self.mx_ledger_repo.rollover_negative_balanced_ledger(
                rollover_negative_ledger_request, self.mx_transaction_repo
            )
            return rolled_mx_ledger
        except DataError as e:
            self.log.error(
                f"[rollover_negative_balanced_ledger_impl] Invalid input data while submitting ledger {mx_ledger_id}, {e}"
            )
            raise MxLedgerSubmissionError(
                error_code=LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR.value
                ],
                retryable=True,
            )
        except OperationalError as e:
            if e.pgcode != LOCK_NOT_AVAILABLE:
                self.log.error(
                    f"[rollover_negative_balanced_ledger_impl] OperationalError caught while rolling over negative balanced ledger {mx_ledger_id}, {e}"
                )
                raise MxLedgerProcessError(
                    error_code=LedgerErrorCode.MX_TXN_OPERATIONAL_ERROR,
                    error_message=ledger_error_message_maps[
                        LedgerErrorCode.MX_TXN_OPERATIONAL_ERROR.value
                    ],
                    retryable=True,
                )
            self.log.warn(
                f"[rollover_negative_balanced_ledger_impl] Cannot obtain lock while rolling over negative balanced ledger {mx_ledger_id}, {e}"
            )
            raise MxLedgerLockError(
                error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
                ],
                retryable=True,
            )
        except IntegrityError as e:
            if e.pgcode != UNIQUE_VIOLATION:
                self.log.error(
                    f"[rollover_negative_balanced_ledger_impl] IntegrityError caught while creating ledger and "
                    f"inserting mx_transaction, {e}"
                )
                raise MxLedgerProcessError(
                    error_code=LedgerErrorCode.MX_LEDGER_CREATE_INTEGRITY_ERROR,
                    error_message=ledger_error_message_maps[
                        LedgerErrorCode.MX_LEDGER_CREATE_INTEGRITY_ERROR.value
                    ],
                    retryable=True,
                )
            self.log.warn(
                f"[rollover_negative_balanced_ledger_impl] Retry to update ledger balance instead of insert "
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

    async def create_mx_ledger(
        self, currency: str, balance: int, payment_account_id: str, type: str
    ):
        """
        Create a mx_ledger
        """
        try:
            if type == MxLedgerType.MICRO_DEPOSIT:
                request_input = InsertMxTransactionWithLedgerInput(
                    currency=currency,
                    amount=balance,
                    type=type,
                    payment_account_id=payment_account_id,
                    routing_key=datetime.utcnow(),
                    idempotency_key=str(uuid.uuid4()),
                    target_type=MxLedgerType.MICRO_DEPOSIT,
                )
                mx_ledger, mx_transaction = await self.mx_transaction_repo.create_ledger_and_insert_mx_transaction_caller(
                    request=request_input
                )
                return mx_ledger, mx_transaction
            raise Exception(
                "By now only is micro-deposit supported for mx_ledger creation"
            )
        except DataError as e:
            self.log.error(
                f"[create_mx_ledger] Invalid input data while creating ledger, {e}"
            )
            raise MxLedgerCreationError(
                error_code=LedgerErrorCode.MX_LEDGER_CREATE_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_CREATE_ERROR.value
                ],
                retryable=True,
            )
        except Exception as e:
            self.log.error(
                f"[create_mx_ledger] Exception caught while creating mx_ledger, {e}"
            )
            raise e
