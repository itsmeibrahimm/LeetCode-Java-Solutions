from uuid import UUID
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.errors import (
    DBOperationError,
    DBIntegrityError,
    DBDataError,
    DBOperationLockNotAvailableError,
    DBIntegrityUniqueViolationError,
)
from app.commons.core.processor import OperationRequest, AsyncOperation
from app.ledger.core.mx_ledger.types import MxLedgerInternal
from app.ledger.repository.mx_ledger_repository import MxLedgerRepositoryInterface
from structlog.stdlib import BoundLogger
from tenacity import (
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    retry,
    wait_fixed,
)

from app.ledger.core.data_types import (
    ProcessMxLedgerInput,
    GetMxLedgerByIdInput,
    UpdatePaidMxLedgerInput,
    ProcessMxLedgerOutput,
    RolloverNegativeLedgerInput,
)
from app.ledger.core.exceptions import (
    LedgerErrorCode,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
    MxLedgerSubmissionError,
    MxLedgerCreateUniqueViolationError,
    MxLedgerLockError,
    MxLedgerProcessError,
)
from app.ledger.core.types import MxLedgerStateType
from app.ledger.core.utils import to_mx_ledger
from app.ledger.repository.mx_transaction_repository import (
    MxTransactionRepositoryInterface,
)


class SubmitMxLedgerRequest(OperationRequest):
    mx_ledger_id: UUID


class SubmitMxLedger(AsyncOperation[SubmitMxLedgerRequest, MxLedgerInternal]):
    """
    Submit mx_ledger to Payout Service and handle negative balance rollover if exists.
    """

    mx_ledger_repo: MxLedgerRepositoryInterface
    mx_transaction_repo: MxTransactionRepositoryInterface

    def __init__(
        self,
        request: SubmitMxLedgerRequest,
        *,
        mx_ledger_repo: MxLedgerRepositoryInterface,
        mx_transaction_repo: MxTransactionRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.mx_ledger_repo = mx_ledger_repo
        self.mx_transaction_repo = mx_transaction_repo

    async def _execute(self) -> MxLedgerInternal:
        """
        Submit mx_ledger to Payout Service and handle negative balance rollover if exists.
        """
        # check whether the given ledger exists or not
        mx_ledger_id = self.request.mx_ledger_id
        retrieve_ledger_request = GetMxLedgerByIdInput(id=mx_ledger_id)
        retrieved_ledger = await self.mx_ledger_repo.get_ledger_by_id(
            retrieve_ledger_request
        )
        if not retrieved_ledger:
            raise MxLedgerReadError(
                error_code=LedgerErrorCode.MX_LEDGER_NOT_FOUND, retryable=False
            )

        # mx_ledger state needs to be PROCESSING in order to be submitted, otherwise raise exception
        if not retrieved_ledger.state == MxLedgerStateType.PROCESSING:
            raise MxLedgerInvalidProcessStateError(
                error_code=LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE,
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
            except DBDataError as e:
                self.logger.error(
                    "[submit mx_ledger] Invalid input data while submitting ledger",
                    mx_ledger_id=mx_ledger_id,
                    error=e,
                )
                raise MxLedgerSubmissionError(
                    error_code=LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR, retryable=True
                )
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
            except DBDataError as e:
                self.logger.error(
                    "[submit mx_ledger] Invalid input data while submitting ledger",
                    mx_ledger_id=mx_ledger_id,
                    error=e,
                )
                raise MxLedgerSubmissionError(
                    error_code=LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR, retryable=True
                )

        else:
            # rollover negative balance mx_ledger
            try:
                mx_ledger = await self._rollover_negative_balanced_ledger_impl(
                    mx_ledger_id
                )
                return to_mx_ledger(mx_ledger)
            except RetryError as e:
                self.logger.error(
                    "[submit mx_ledger] Failed to retry rolling over mx_ledger",
                    mx_ledger_id=mx_ledger_id,
                    error=e,
                )
                raise MxLedgerSubmissionError(
                    error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                    retryable=True,
                )

    def _handle_exception(self, internal_exec: BaseException):
        if isinstance(internal_exec, MxLedgerReadError):
            raise PaymentException(
                http_status_code=HTTP_404_NOT_FOUND,
                error_code=internal_exec.error_code,
                error_message=internal_exec.error_message,
                retryable=internal_exec.retryable,
            )
        elif isinstance(internal_exec, MxLedgerInvalidProcessStateError):
            raise PaymentException(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=internal_exec.error_code,
                error_message=internal_exec.error_message,
                retryable=internal_exec.retryable,
            )
        raise DEFAULT_INTERNAL_EXCEPTION

    @retry(
        retry=(
            retry_if_exception_type(MxLedgerCreateUniqueViolationError)
            | retry_if_exception_type(MxLedgerLockError)
        ),
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.3),
    )
    async def _rollover_negative_balanced_ledger_impl(
        self, mx_ledger_id: UUID
    ) -> ProcessMxLedgerOutput:
        rollover_negative_ledger_request = RolloverNegativeLedgerInput(id=mx_ledger_id)
        try:
            rolled_mx_ledger = await self.mx_ledger_repo.rollover_negative_balanced_ledger(
                rollover_negative_ledger_request, self.mx_transaction_repo
            )
            return rolled_mx_ledger
        except DBDataError as e:
            self.logger.error(
                "[rollover_negative_balanced_ledger_impl] Invalid input data while submitting ledger",
                mx_ledger_id=mx_ledger_id,
                error=e,
            )
            raise MxLedgerSubmissionError(
                error_code=LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR, retryable=True
            )
        except DBOperationLockNotAvailableError as e:
            self.logger.warn(
                "[rollover_negative_balanced_ledger_impl] Cannot obtain lock while rolling over negative balanced ledger",
                mx_ledger_id=mx_ledger_id,
                error=e,
            )
            raise MxLedgerLockError(
                error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                retryable=True,
            )
        except DBOperationError as e:
            self.logger.error(
                "[rollover_negative_balanced_ledger_impl] OperationalError caught while rolling over negative balanced ledger",
                mx_ledger_id=mx_ledger_id,
                error=e,
            )
            raise MxLedgerProcessError(
                error_code=LedgerErrorCode.MX_TXN_OPERATIONAL_ERROR, retryable=True
            )
        except DBIntegrityUniqueViolationError as e:
            self.logger.warn(
                "[rollover_negative_balanced_ledger_impl] Retry to update ledger balance instead of insert due to unique constraints violation",
                error=e,
            )
            # retry with insert_mx_txn_and_update_ledger due to unique constraints violation
            raise MxLedgerCreateUniqueViolationError(
                error_code=LedgerErrorCode.MX_LEDGER_CREATE_UNIQUE_VIOLATION_ERROR,
                retryable=True,
            )
        except DBIntegrityError as e:
            self.logger.error(
                "[rollover_negative_balanced_ledger_impl] IntegrityError caught while creating ledger and inserting mx_transaction",
                error=e,
            )
            raise MxLedgerProcessError(
                error_code=LedgerErrorCode.MX_LEDGER_CREATE_INTEGRITY_ERROR,
                retryable=True,
            )
