from uuid import UUID

from fastapi import Depends
from psycopg2._psycopg import DataError, OperationalError
from psycopg2.errorcodes import LOCK_NOT_AVAILABLE
from structlog import BoundLogger
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
)
from app.ledger.core.exceptions import (
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerProcessError,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
    MxLedgerLockError,
    MxLedgerSubmissionError,
)
from app.ledger.core.mx_ledger.model import MxLedger
from app.ledger.core.types import MxLedgerStateType
from app.ledger.core.utils import to_mx_ledger
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository


class MxLedgerProcessor:
    def __init__(
        self,
        mx_transaction_repo: MxTransactionRepository = Depends(
            MxTransactionRepository.get_repository
        ),
        mx_ledger_repo: MxLedgerRepository = Depends(MxLedgerRepository.get_repository),
        mx_scheduled_ledger_repo: MxScheduledLedgerRepository = Depends(
            MxScheduledLedgerRepository.get_repository
        ),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.mx_transaction_repo = mx_transaction_repo
        self.mx_scheduled_ledger_repo = mx_scheduled_ledger_repo
        self.mx_ledger_repo = mx_ledger_repo
        self.log = log

    async def process(self, mx_ledger_id: UUID) -> MxLedger:
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
                retryable=True,
            )
        # mx_ledger state needs to be OPEN in order to be processed, otherwise raise exception
        if not retrieved_ledger.state == MxLedgerStateType.OPEN:
            raise MxLedgerInvalidProcessStateError(
                error_code=LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE.value
                ],
                retryable=True,
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
    async def process_ledger_and_scheduled_ledger(self, mx_ledger_id: UUID):
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

    async def submit(self, mx_ledger_id: UUID) -> MxLedger:
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
                retryable=True,
            )

        # mx_ledger state needs to be PROCESSING in order to be submitted, otherwise raise exception
        if not retrieved_ledger.state == MxLedgerStateType.PROCESSING:
            raise MxLedgerInvalidProcessStateError(
                error_code=LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE,
                error_message=ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE.value
                ],
                retryable=True,
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
                    f"[submit mx_ledger] Invalid input data while processing ledger {mx_ledger_id}, {e}"
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
        # elif retrieved_ledger.balance == 0:
        else:
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
                    f"[submit mx_ledger] Invalid input data while processing ledger {mx_ledger_id}, {e}"
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

    #     else:
    #         # process negative balance mx_ledger
    #         try:
    #             # todo: move this function into ledger repo in order to obtain db connection
    #             mx_ledger = await self.rollover_negative_balanced_ledger(mx_ledger_id)
    #             return to_mx_ledger(mx_ledger)
    #         except RetryError as e:
    #             self.log.error(
    #                 f"[submit mx_ledger] Failed to retry locking mx_ledger {mx_ledger_id}, {e}"
    #             )
    #             raise MxLedgerSubmissionError(
    #                 error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
    #                 error_message=ledger_error_message_maps[
    #                     LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
    #                 ],
    #                 retryable=True,
    #             )
    #
    # @retry(
    #     retry=retry_if_exception_type(MxLedgerLockError),
    #     stop=stop_after_attempt(5),
    #     wait=wait_fixed(0.3),
    # )
    # async def rollover_negative_balanced_ledger(self, mx_ledger_id: UUID) -> MxLedger:
    #
    #     # todo: replace with Min's refactor after merged
    #     # just assume the given ledger id is valid for now
    #     retrieve_ledger_request = GetMxLedgerByIdInput(id=mx_ledger_id)
    #     retrieved_ledger = await self.mx_ledger_repo.get_ledger_by_id(
    #         retrieve_ledger_request
    #     )
    #     assert retrieved_ledger
    #
    #     # check whether there is another open ledger(we use open scheduled_ledger to represent open ledger) for the payment account
    #     retrieve_scheduled_ledger_request = GetMxScheduledLedgerByAccountInput(
    #         payment_account_id=retrieved_ledger.payment_account_id
    #     )
    #     mx_scheduled_ledger = await self.mx_transaction_repo.get_open_mx_scheduled_ledger_for_payment_account_id(
    #         retrieve_scheduled_ledger_request
    #     )
    #     open_ledger = None
    #     # if so, rollover the mx_ledger to the open ledger and create negative balance txn
    #     if mx_scheduled_ledger:
    #         open_ledger_id = mx_scheduled_ledger.ledger_id
    #         rollover_negative_ledger_request = RolloverNegativeLedgerInput(
    #             id=mx_ledger_id
    #         )
    #         try:
    #             open_ledger = await self.mx_ledger_repo.rollover_negative_ledger_to_open_ledger(
    #                 rollover_negative_ledger_request, open_ledger_id
    #             )
    #         except DataError as e:
    #             self.log.error(
    #                 f"[process negative balance mx_ledger] Invalid input data while processing negative balance mx_ledger to open ledger, {e}"
    #             )
    #
    #             raise MxLedgerSubmissionError(
    #                 error_code=LedgerErrorCode.MX_LEDGER_ROLLOVER_ERROR,
    #                 error_message=ledger_error_message_maps[
    #                     LedgerErrorCode.MX_LEDGER_ROLLOVER_ERROR.value
    #                 ],
    #                 retryable=True,
    #             )
    #         except OperationalError as e:
    #             if e.pgcode != LOCK_NOT_AVAILABLE:
    #                 self.log.error(
    #                     f"[process negative balance mx_ledger] OperationalError caught while processing negative balance mx_ledger to open ledger, {e}"
    #                 )
    #                 raise MxLedgerSubmissionError(
    #                     error_code=LedgerErrorCode.MX_LEDGER_OPERATIONAL_ERROR,
    #                     error_message=ledger_error_message_maps[
    #                         LedgerErrorCode.MX_LEDGER_OPERATIONAL_ERROR.value
    #                     ],
    #                     retryable=True,
    #                 )
    #             self.log.warn(
    #                 f"[process negative balance mx_ledger] Cannot obtain lock for mx_ledger {e}"
    #             )
    #             # todo: retry needed here
    #             raise MxLedgerSubmissionError(
    #                 error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
    #                 error_message=ledger_error_message_maps[
    #                     LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
    #                 ],
    #                 retryable=True,
    #             )
    #         except Exception as e:
    #             self.log.error(
    #                 f"[process negative balance mx_ledger] Error caught while processing negative balance mx_ledger to open ledger, {e}"
    #             )
    #             raise e
    #     else:
    #         # if not, rollover the mx_ledger to a newly created ledger with negative balance initialized
    #         rollover_negative_ledger_request = RolloverNegativeLedgerInput(
    #             id=retrieved_ledger.id
    #         )
    #         try:
    #             open_ledger = await self.mx_ledger_repo.rollover_negative_ledger_to_new_ledger(
    #                 rollover_negative_ledger_request
    #             )
    #         except DataError as e:
    #             self.log.error(
    #                 f"[process negative balance mx_ledger] Invalid input data while processing negative balance mx_ledger to new ledger, {e}"
    #             )
    #
    #             raise MxLedgerSubmissionError(
    #                 error_code=LedgerErrorCode.MX_LEDGER_ROLLOVER_ERROR,
    #                 error_message=ledger_error_message_maps[
    #                     LedgerErrorCode.MX_LEDGER_ROLLOVER_ERROR.value
    #                 ],
    #                 retryable=True,
    #             )
    #         except OperationalError as e:
    #             if e.pgcode != LOCK_NOT_AVAILABLE:
    #                 self.log.error(
    #                     f"[process negative balance mx_ledger] OperationalError caught while processing negative balance mx_ledger to new ledger, {e}"
    #                 )
    #                 raise MxLedgerSubmissionError(
    #                     error_code=LedgerErrorCode.MX_LEDGER_OPERATIONAL_ERROR,
    #                     error_message=ledger_error_message_maps[
    #                         LedgerErrorCode.MX_LEDGER_OPERATIONAL_ERROR.value
    #                     ],
    #                     retryable=True,
    #                 )
    #             self.log.warn(
    #                 f"[process negative balance mx_ledger] Cannot obtain lock for mx_ledger {e}"
    #             )
    #             # todo: retry needed here
    #             raise MxLedgerSubmissionError(
    #                 error_code=LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR,
    #                 error_message=ledger_error_message_maps[
    #                     LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
    #                 ],
    #                 retryable=True,
    #             )
    #         except psycopg2.IntegrityError as e:
    #             # todo: needs to be wrapped up
    #             if e.pgcode != UNIQUE_VIOLATION:
    #                 raise
    #             self.log.warn(
    #                 f"[process negative balance mx_ledger] Retry to rollover to open ledger instead of new ledger due to unique constraints violation, {e}"
    #             )
    #             # todo: retry needed here
    #         except Exception as e:
    #             self.log.error(
    #                 f"[process negative balance mx_ledger] Error caught while processing negative balance mx_ledger to new ledger, {e}"
    #             )
    #             raise e
    #
    #     # update negative balance ledger states to ROLLED
    #     # todo: need to update as mx_transaction after Min's pr
    #     assert open_ledger
    #     submit_ledger_request = UpdatedRolledMxLedgerInput(
    #         id=mx_ledger_id, rolled_to_ledger_id=open_ledger.id
    #     )
    #     try:
    #         mx_ledger = await self.mx_ledger_repo.move_ledger_state_to_rolled(
    #             submit_ledger_request
    #         )
    #         return to_mx_ledger(mx_ledger)
    #     except Exception as e:
    #         raise e
