import inspect
import json
import logging
from typing import Optional

from aiokafka import AIOKafkaProducer

from app.commons.context.app_context import AppContext
from app.payout.models import PayoutTask

log = logging.getLogger(__name__)


def normalize_task_arguments(frame) -> dict:
    fn_kwargs = {}
    args, _, _, values = inspect.getargvalues(frame)
    for i in args:
        if not i == "self":
            fn_kwargs[i] = values[i]
    return fn_kwargs


class BaseTask:
    topic_name: str
    task_type: PayoutTask
    max_retries: int
    attempts: int
    fn_args: list
    fn_kwargs: Optional[dict] = None

    def __init__(
        self, topic_name, task_type, max_retries, attempts, fn_args, fn_kwargs
    ):
        self.topic_name = topic_name
        self.task_type = task_type
        self.max_retries = max_retries
        self.attempts = attempts
        self.fn_args = fn_args
        self.fn_kwargs = fn_kwargs

    @staticmethod
    def create_transfer_task():
        from app.payout.core.transfer.tasks.create_transfer_task import (
            CreateTransferTask,
        )

        return CreateTransferTask

    @staticmethod
    def submit_transfer_task():
        from app.payout.core.transfer.tasks.submit_transfer_task import (
            SubmitTransferTask,
        )

        return SubmitTransferTask

    @staticmethod
    def weekly_create_transfer_task():
        from app.payout.core.transfer.tasks.weekly_create_transfer_task import (
            WeeklyCreateTransferTask,
        )

        return WeeklyCreateTransferTask

    async def execute(self, app_context: AppContext, data: dict):
        task_type_mapping = {
            "weekly_create_transfer": self.weekly_create_transfer_task(),
            "create_transfer": self.create_transfer_task(),
            "submit_transfer": self.submit_transfer_task(),
        }

        task = task_type_mapping.get(self.task_type, None)
        if task:
            try:
                await task.run(app_context=app_context, data=data)
            except Exception as e:
                # Retry for all kinds of exceptions depending on the max_retries set by each task
                if self.attempts < self.max_retries:
                    log.info(
                        "[BaseTask execute] task execution failure. Retrying.",
                        extra={"attempts": self.attempts, "task_type": self.task_type},
                        exc_info=e,
                    )
                    self.attempts += 1
                    await self.send(kafka_producer=app_context.kafka_producer)
                else:
                    log.info(
                        "[BaseTask execute] Exceeded max_retries. Drop the task.",
                        extra={
                            "max_retries": self.max_retries,
                            "task_type": self.task_type,
                        },
                    )

            log.info("[BaseTask execute] Finished processing message")
        else:
            log.warning(
                "[BaseTask execute] Unsupported task type.",
                extra={"task_type": data["task_type"]},
            )

    async def send(self, kafka_producer: AIOKafkaProducer):
        await kafka_producer.send_and_wait(self.topic_name, self.serialize().encode())

    @staticmethod
    async def run(app_context: AppContext, data: dict):
        pass

    def serialize(self) -> str:
        data = {
            "topic_name": self.topic_name,
            "task_type": self.task_type,
            "max_retries": self.max_retries,
            "attempts": self.attempts,
            "fn_args": self.fn_args,
            "fn_kwargs": self.fn_kwargs,
        }
        return json.dumps(data)

    @staticmethod
    def deserialize(json_data):
        return BaseTask(**json_data)
