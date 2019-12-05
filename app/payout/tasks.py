import logging

from app.commons.context.app_context import AppContext

log = logging.getLogger(__name__)


async def process_message(app_context: AppContext, message: str):
    # if random.random() < 0.10:
    #     raise RuntimeError("test task failure")

    # await asyncio.sleep(random.random() * 3)
    log.info(f"finished processing message: {message}")
    return True
