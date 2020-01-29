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
from app.commons.providers.dsj_client import DSJClient
from app.payout.constants import DAILY_TRANSFER_BUSINESS_IDS
from app.payout.core.transfer.tasks.create_transfer_task import CreateTransferTask
from app.payout.core.transfer.utils import get_payment_account_ids_with_biz_id
from app.commons.runtime import runtime


class DailyCreateTransfersByBusinessResponse(OperationResponse):
    pass


class DailyCreateTransfersByBusinessRequest(OperationRequest):
    end_time: datetime


class DailyCreateTransfersByBusiness(
    AsyncOperation[
        DailyCreateTransfersByBusinessRequest, DailyCreateTransfersByBusinessResponse
    ]
):
    """
    Processor to retrieve
    """

    dsj_client: DSJClient
    kafka_producer: KafkaMessageProducer

    def __init__(
        self,
        request: DailyCreateTransfersByBusinessRequest,
        *,
        dsj_client: DSJClient,
        kafka_producer: KafkaMessageProducer,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.dsj_client = dsj_client
        self.kafka_producer = kafka_producer

    async def _execute(self) -> DailyCreateTransfersByBusinessResponse:
        self.logger.info(
            "[daily_create_transfers_by_business] Start retrieving daily payout account ids",
            end_time=self.request.end_time,
        )

        payment_account_ids = await self.get_daily_payout_payment_account_ids()
        for payment_account_id in payment_account_ids:
            self.logger.info(
                "[daily_create_transfers_by_business] Enqueuing transfer for account",
                payment_account_id=payment_account_id,
            )
            create_transfer_task = CreateTransferTask(
                payout_account_id=payment_account_id,
                end_time=self.request.end_time.isoformat(),
                submit_after_creation=True,
                payout_countries=None,
                payout_day=None,
                start_time=None,
            )
            await create_transfer_task.send(kafka_producer=self.kafka_producer)
        self.logger.info(
            "[daily_create_transfers_by_business] Finished executing daily create transfers by business",
            end_time=self.request.end_time,
        )
        return DailyCreateTransfersByBusinessResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, DailyCreateTransfersByBusinessResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION

    async def get_daily_payout_payment_account_ids(self):
        """
        Find daily payout payment account ids with whitelisted daily payout business ids
        """
        b_ids = runtime.get_json(DAILY_TRANSFER_BUSINESS_IDS, [])
        payment_account_ids = []
        for business_id in b_ids:
            retrieved_account_ids = await get_payment_account_ids_with_biz_id(
                business_id=business_id, dsj_client=self.dsj_client
            )
            payment_account_ids.extend(retrieved_account_ids)
        return payment_account_ids
