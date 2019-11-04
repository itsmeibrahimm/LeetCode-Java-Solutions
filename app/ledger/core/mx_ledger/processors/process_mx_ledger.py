from uuid import UUID
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.errors import (
    DBDataError,
    DBOperationError,
    DBOperationLockNotAvailableError,
)
from app.commons.core.processor import OperationRequest, AsyncOperation
from app.ledger.core.mx_ledger.types import MxLedgerInternal
from app.ledger.repository.mx_ledger_repository import MxLedgerRepositoryInterface
import uuid
from structlog.stdlib import BoundLogger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
    RetryError,
)
from app.ledger.core.data_types import ProcessMxLedgerInput, GetMxLedgerByIdInput
from app.ledger.core.exceptions import (
    LedgerErrorCode,
    MxLedgerProcessError,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
    MxLedgerLockError,
)
from app.ledger.core.types import MxLedgerStateType
from app.ledger.core.utils import to_mx_ledger


class ProcessMxLedgerRequest(OperationRequest):
    mx_ledger_id: UUID


class ProcessMxLedger(AsyncOperation[ProcessMxLedgerRequest, MxLedgerInternal]):
    """
    Move mx_ledger to PROCESSING and close mx_scheduled_ledger.
    """

    mx_ledger_repo: MxLedgerRepositoryInterface

    def __init__(
        self,
        request: ProcessMxLedgerRequest,
        *,
        mx_ledger_repo: MxLedgerRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.mx_ledger_repo = mx_ledger_repo

    async def _execute(self) -> MxLedgerInternal:
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
        # mx_ledger state needs to be OPEN in order to be processed, otherwise raise exception
        if not retrieved_ledger.state == MxLedgerStateType.OPEN:
            raise MxLedgerInvalidProcessStateError(
                error_code=LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE,
                retryable=False,
            )
        # process mx_ledger and close scheduled_ledger
        try:
            mx_ledger = await self.process_ledger_and_scheduled_ledger(mx_ledger_id)
            return to_mx_ledger(mx_ledger)
        except RetryError as e:
            self.logger.error(
                "[process mx_ledger] Failed to retry locking mx_ledger",
                mx_ledger_id=mx_ledger_id,
                error=e,
            )
            raise MxLedgerProcessError(
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
        except DBDataError as e:
            self.logger.error(
                "[process_ledger_and_scheduled_ledger] Invalid input data while processing ledger",
                mx_ledger_id=mx_ledger_id,
                error=e,
            )
            raise MxLedgerProcessError(
                error_code=LedgerErrorCode.MX_LEDGER_PROCESS_ERROR, retryable=True
            )
        except DBOperationLockNotAvailableError as e:
            self.logger.warn(
                "[process_ledger_and_scheduled_ledger] Cannot obtain lock while updating ledger",
                mx_ledger_id=mx_ledger_id,
                error=e,
            )
            raise MxLedgerLockError(
                error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
                retryable=True,
            )
        except DBOperationError as e:
            self.logger.error(
                "[process_ledger_and_scheduled_ledger] OperationalError caught while processing ledger",
                mx_ledger_id=mx_ledger_id,
                error=e,
            )
            raise MxLedgerProcessError(
                error_code=LedgerErrorCode.MX_TXN_OPERATIONAL_ERROR, retryable=True
            )
        except Exception as e:
            self.logger.error(
                "[process_ledger_and_scheduled_ledger] Exception caught while processing ledger",
                error=e,
            )
            raise e
