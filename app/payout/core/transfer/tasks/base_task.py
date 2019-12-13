import inspect
import json
from typing import Optional, List

from aiokafka import AIOKafkaProducer

from app.commons.context.app_context import AppContext
from app.payout.models import PayoutTask


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
    auto_retry_for: List[Exception]
    max_retries: int
    fn_args: list
    fn_kwargs: Optional[dict] = None

    def __init__(
        self, topic_name, task_type, auto_retry_for, max_retries, fn_args, fn_kwargs
    ):
        self.topic_name = topic_name
        self.task_type = task_type
        self.auto_retry_for = auto_retry_for
        self.max_retries = max_retries
        self.fn_args = fn_args
        self.fn_kwargs = fn_kwargs

    async def send(self, kafka_producer: AIOKafkaProducer):
        await kafka_producer.send_and_wait(self.topic_name, self.serialize().encode())

    @staticmethod
    async def run(app_context: AppContext, data: dict):
        pass

    def serialize(self) -> str:
        data = {
            "topic_name": self.topic_name,
            "task_type": self.task_type,
            "auto_retry_for": self.auto_retry_for,
            "max_retries": self.max_retries,
            "fn_args": self.fn_args,
            "fn_kwargs": self.fn_kwargs,
        }
        return json.dumps(data)

    def deserialize(self, message: str):
        pass
