from uuid import UUID

from psycopg2._psycopg import DataError
from fastapi import Depends
from structlog import BoundLogger
from app.commons.context.req_context import get_logger_from_req
from app.ledger.core.data_types import ProcessMxLedgerInput
from app.ledger.core.exceptions import (
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerProcessError,
)
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository


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
        Move mx_ledger from OPEN to PROCESSING
        """
        process_mx_ledger_request = ProcessMxLedgerInput(id=mx_ledger_id)
        try:
            mx_ledger = await self.mx_ledger_repo.process_mx_ledger_state(
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
