import json
from app.commons.context.app_context import AppContext
from app.payout.core.transfer.tasks.base_task import BaseTask


async def process_message(app_context: AppContext, message: str):
    data = json.loads(message)
    base_task = BaseTask.deserialize(data)
    await base_task.execute(app_context=app_context, data=data)
