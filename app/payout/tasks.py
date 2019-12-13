import json
import logging
from app.commons.context.app_context import AppContext
from app.payout.core.transfer.tasks.create_transfer_task import CreateTransferTask
from app.payout.core.transfer.tasks.submit_transfer_task import SubmitTransferTask
from app.payout.core.transfer.tasks.weekly_create_transfer_task import (
    WeeklyCreateTransferTask,
)
from app.payout.models import PayoutTask

log = logging.getLogger(__name__)


async def process_message(app_context: AppContext, message: str):
    data = json.loads(message)
    if data["task_type"] == PayoutTask.WEEKLY_CREATE_TRANSFER.value:
        await WeeklyCreateTransferTask.run(app_context, data)
    elif data["task_type"] == PayoutTask.CREATE_TRANSFER.value:
        await CreateTransferTask.run(app_context, data)
    elif data["task_type"] == PayoutTask.SUBMIT_TRANSFER.value:
        await SubmitTransferTask.run(app_context, data)

    log.info(f"finished processing message: {message}")
    return True
