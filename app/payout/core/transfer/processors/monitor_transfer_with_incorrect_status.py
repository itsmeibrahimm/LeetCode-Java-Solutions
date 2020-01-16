from datetime import datetime

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union

from app.commons.async_kafka_producer import KafkaMessageProducer
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.constants import (
    ENABLE_QUEUEING_MECHANISM_FOR_MONITOR_TRANSFER_WITH_INCORRECT_STATUS,
)
from app.payout.core.transfer.processors.update_transfer_by_stripe_transfer_status import (
    UpdateTransferByStripeTransferStatusRequest,
    UpdateTransferByStripeTransferStatus,
)
from app.payout.core.transfer.tasks.update_transfer_by_stripe_transfer_status_task import (
    UpdateTransferByStripeTransferStatusTask,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.repository.maindb.transfer import TransferRepositoryInterface
from app.commons.runtime import runtime


class MonitorTransferWithIncorrectStatusResponse(OperationResponse):
    pass


class MonitorTransferWithIncorrectStatusRequest(OperationRequest):
    start_time: datetime


class MonitorTransferWithIncorrectStatus(
    AsyncOperation[
        MonitorTransferWithIncorrectStatusRequest,
        MonitorTransferWithIncorrectStatusResponse,
    ]
):
    """
    Processor to search transfers with given payment account ids.
    """

    transfer_repo: TransferRepositoryInterface
    stripe_transfer_repo: StripeTransferRepositoryInterface
    stripe: StripeAsyncClient
    kafka_producer: KafkaMessageProducer

    def __init__(
        self,
        request: MonitorTransferWithIncorrectStatusRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        stripe: StripeAsyncClient,
        kafka_producer: KafkaMessageProducer,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.stripe = stripe
        self.kafka_producer = kafka_producer

    async def _execute(self) -> MonitorTransferWithIncorrectStatusResponse:
        transfer_ids = await self.transfer_repo.get_transfers_by_submitted_at_and_method(
            start_time=self.request.start_time
        )
        enable_queuing_mechanism_for_monitor_transfer = runtime.get_bool(
            ENABLE_QUEUEING_MECHANISM_FOR_MONITOR_TRANSFER_WITH_INCORRECT_STATUS, False
        )
        for transfer_id in transfer_ids:
            if enable_queuing_mechanism_for_monitor_transfer:
                # put update_transfer_by_stripe_transfer_status into queue
                self.logger.info(
                    "Enqueuing update_transfer_by_stripe_transfer_status task",
                    transfer_id=transfer_id,
                )
                update_transfer_by_stripe_transfer_status_task = UpdateTransferByStripeTransferStatusTask(
                    transfer_id=transfer_id
                )
                await update_transfer_by_stripe_transfer_status_task.send(
                    kafka_producer=self.kafka_producer
                )
            else:
                update_transfer_by_stripe_transfer_status_req = UpdateTransferByStripeTransferStatusRequest(
                    transfer_id=transfer_id
                )
                update_transfer_by_stripe_transfer_status_op = UpdateTransferByStripeTransferStatus(
                    transfer_repo=self.transfer_repo,
                    stripe_transfer_repo=self.stripe_transfer_repo,
                    stripe=self.stripe,
                    logger=self.logger,
                    request=update_transfer_by_stripe_transfer_status_req,
                )
                await update_transfer_by_stripe_transfer_status_op.execute()

        return MonitorTransferWithIncorrectStatusResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, MonitorTransferWithIncorrectStatusResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
