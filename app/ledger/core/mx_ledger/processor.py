from uuid import UUID

from psycopg2._psycopg import DataError
from fastapi import Depends
from structlog import BoundLogger
from app.commons.context.req_context import get_logger_from_req
from app.ledger.core.data_types import ProcessMxLedgerInput, GetMxLedgerByIdInput
from app.ledger.core.exceptions import (
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerProcessError,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
)
from app.ledger.core.types import MxLedgerStateType
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository

STATES_CAN_MOVE_TO_PROCESSING = [
    MxLedgerStateType.OPEN,
    MxLedgerStateType.FAILED,
    MxLedgerStateType.FAILED,
]


class MxLedgerProcessor:
    def __init__(
        self,
        mx_ledger_repo: MxLedgerRepository = Depends(MxLedgerRepository.get_repository),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.mx_ledger_repo = mx_ledger_repo
        self.log = log

    async def process(self, mx_ledger_id: UUID):
        """
        Move mx_ledger to PROCESSING
        """
        # check if the given ledger exists
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
                retryable=True,
            )
        # mx_ledger state needs to be OPEN, FAILED or REVERSED in order to be processed, otherwise raise exception
        if retrieved_ledger.state not in STATES_CAN_MOVE_TO_PROCESSING:
            raise MxLedgerInvalidProcessStateError(
                error_code=LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE.value
                ],
                retryable=True,
            )

        # process mx_ledger
        process_mx_ledger_request = ProcessMxLedgerInput(id=mx_ledger_id)
        try:
            mx_ledger = await self.mx_ledger_repo.process_mx_ledger_state_and_close_schedule_ledger(
                process_mx_ledger_request
            )
        except DataError as e:
            self.log.error(
                f"[process mx_ledger] Invalid input data while processing ledger, {e}"
            )
            raise MxLedgerProcessError(
                error_code=LedgerErrorCode.MX_LEDGER_PROCESS_ERROR,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_PROCESS_ERROR.value
                ],
                retryable=True,
            )
        except Exception as e:
            self.log.error(
                f"[process mx_ledger] Exception caught while processing ledger, {e}"
            )
            raise e
        return mx_ledger
