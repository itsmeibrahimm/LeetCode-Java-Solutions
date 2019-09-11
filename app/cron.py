import asyncio
import os
import signal

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.commons.config.utils import init_app_config
from app.commons.context.app_context import create_app_context
from app.commons.context.logger import get_logger
from app.commons.stats import init_global_statsd
from app.payin.jobs import (
    capture_uncaptured_payment_intents,
    resolve_capturing_payment_intents,
)
from app.payin.repository.cart_payment_repo import CartPaymentRepository

config = init_app_config()
if config.SENTRY_CONFIG:
    sentry_sdk.init(
        dsn=config.SENTRY_CONFIG.dsn.value,
        environment=config.SENTRY_CONFIG.environment,
        release=config.SENTRY_CONFIG.release,
    )

# set up global statsd
init_global_statsd(
    prefix=config.GLOBAL_STATSD_PREFIX,
    host=config.STATSD_SERVER,
    fixed_tags={"env": config.ENVIRONMENT},
)

logger = get_logger("cron")


def run_scheduler():
    scheduler = AsyncIOScheduler()
    loop = asyncio.get_event_loop()
    context_coroutine = create_app_context(config)
    app_context = loop.run_until_complete(context_coroutine)
    cart_payment_repo = CartPaymentRepository(app_context)

    scheduler.add_job(
        capture_uncaptured_payment_intents,
        "cron",
        minute="*/5",
        kwargs={"app_context": app_context, "cart_payment_repo": cart_payment_repo},
    )

    scheduler.add_job(
        resolve_capturing_payment_intents,
        "cron",
        minute="*/5",
        kwargs={"app_context": app_context, "cart_payment_repo": cart_payment_repo},
    )

    scheduler.start()

    async def shutdown():
        print("Received scheduler shutdown request")
        scheduler.shutdown()
        loop.stop()
        print("Done shutting down!")

    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown()))

    print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))

    # Execution will block here until Ctrl+C (Ctrl+Break on Windows) is pressed.

    loop.run_forever()


if __name__ == "__main__":
    run_scheduler()
