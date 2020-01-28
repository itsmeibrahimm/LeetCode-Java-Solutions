from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, List

from app.commons.async_kafka_producer import KafkaMessageProducer
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.core.transfer.tasks.submit_transfer_task import SubmitTransferTask
from app.payout.models import TransferId
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
from app.payout.repository.maindb.model.transfer import TransferUpdate, TransferStatus
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


class MonitorCreatingStatusTransferResponse(OperationResponse):
    pass


class MonitorCreatingStatusTransferRequest(OperationRequest):
    transfer_ids: List[TransferId]


class MonitorCreatingStatusTransfer(
    AsyncOperation[
        MonitorCreatingStatusTransferRequest, MonitorCreatingStatusTransferResponse
    ]
):
    """
    Processor to correct transfers with creating status
    """

    transfer_repo: TransferRepositoryInterface
    transaction_repo: TransactionRepositoryInterface
    kafka_producer: KafkaMessageProducer

    def __init__(
        self,
        request: MonitorCreatingStatusTransferRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        transaction_repo: TransactionRepositoryInterface,
        kafka_producer: KafkaMessageProducer,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo
        self.transaction_repo = transaction_repo
        self.kafka_producer = kafka_producer

    async def _execute(self) -> MonitorCreatingStatusTransferResponse:
        for transfer_id in self.request.transfer_ids:
            transfer = await self.transfer_repo.get_transfer_by_id(
                transfer_id=transfer_id
            )
            if not transfer:
                self.logger.info(
                    "[Monitor Creating Status Transfers] Not found transfer with given id",
                    transfer_id=transfer_id,
                )
                continue
            transactions = await self.transaction_repo.get_transaction_by_transfer_id_without_limit(
                transfer_id=transfer.id
            )
            # transactions were updated before transfer status updated to "new".
            # this failure would only happen if the python process died between updating transaction.transfer_id
            # and saving to maindb Transfer.
            # not expecting this to happen at all.
            if len(transactions) > 0:
                if transfer.amount != sum(txn.amount for txn in transactions):
                    self.logger.error(
                        "[Monitor Creating Status Transfers] Amount for retrieved transactions does not match transfer amount when monitoring transfers in creating status",
                        transfer_id=transfer_id,
                    )
                    continue
                self.logger.info(
                    "[Monitor Creating Status Transfers] Updating transfer status to NEW",
                    transfer_id=transfer.id,
                    transaction_count=len(transactions),
                )
                updated_transfer = await self.transfer_repo.update_transfer_by_id(
                    transfer_id=transfer.id,
                    data=TransferUpdate(status=TransferStatus.NEW),
                )
                if not updated_transfer:
                    self.logger.info(
                        "[Monitor Creating Status Transfers] Not found updated_transfer with given id",
                        transfer_id=transfer_id,
                    )
                    continue
                submit_transfer_task = SubmitTransferTask(
                    transfer_id=updated_transfer.id,
                    method=updated_transfer.method,
                    retry=False,
                    submitted_by=None,
                )
                await submit_transfer_task.send(kafka_producer=self.kafka_producer)
            else:
                self.logger.info(
                    "[Monitor Creating Status Transfers] No transactions attached to transfer, setting status to DELETED",
                    transfer_id=transfer.id,
                )
                await self.transfer_repo.update_transfer_by_id(
                    transfer_id=transfer.id,
                    data=TransferUpdate(status=TransferStatus.DELETED),
                )
        self.logger.info(
            "[Monitor Creating Status Transfers Job] Finished executing monitor creating status transfers"
        )
        return MonitorCreatingStatusTransferResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, MonitorCreatingStatusTransferResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
