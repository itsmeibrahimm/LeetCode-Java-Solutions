import inspect
from uuid import uuid4

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payout.core.transfer.processors.daily_create_transfers_by_business import (
    DailyCreateTransfersByBusinessRequest,
    DailyCreateTransfersByBusiness,
)
from app.payout.core.transfer.tasks.base_task import BaseTask, normalize_task_arguments
from app.payout.models import PayoutTask


class DailyCreateTransfersByBusinessTask(BaseTask):
    def __init__(self, end_time: str):
        self.topic_name = "payment_payout"
        self.task_type = PayoutTask.DAILY_CREATE_TRANSFERS_BY_BUSINESS
        max_retries: int = 5
        attempts: int = 0
        fn_args: list = []
        super().__init__(
            self.topic_name,
            self.task_type,
            max_retries,
            attempts,
            fn_args,
            normalize_task_arguments(inspect.currentframe()),
        )

    @staticmethod
    async def run(app_context: AppContext, data: dict):
        # convert to create transfer for account
        req_context = build_req_context(
            app_context,
            task_name="DailyCreateTransfersByBusinessTask",
            task_id=str(uuid4()),
        )
        daily_create_transfers_by_business_req_dict = {}
        if "fn_kwargs" in data:
            data_kwargs = data["fn_kwargs"]
            for k, v in data_kwargs.items():
                daily_create_transfers_by_business_req_dict[k] = v

        daily_create_transfers_by_business_op_dict = {
            "kafka_producer": app_context.kafka_producer,
            "dsj_client": app_context.dsj_client,
            "logger": req_context.log,
            "request": DailyCreateTransfersByBusinessRequest(
                **daily_create_transfers_by_business_req_dict
            ),
        }
        daily_create_transfers_by_business_op = DailyCreateTransfersByBusiness(
            **daily_create_transfers_by_business_op_dict
        )
        await daily_create_transfers_by_business_op.execute()
