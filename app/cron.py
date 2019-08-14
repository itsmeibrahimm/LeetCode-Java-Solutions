import asyncio
import os
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.commons.config.utils import init_app_config
from app.commons.context.app_context import create_app_context
from app.payin.jobs import capture_uncaptured_payment_intents
from app.payin.repository.cart_payment_repo import CartPaymentRepository


def run_scheduler():
    scheduler = AsyncIOScheduler()
    config = init_app_config()
    loop = asyncio.get_event_loop()
    context_coroutine = create_app_context(config)
    app_context = loop.run_until_complete(context_coroutine)
    cart_payment_repo = CartPaymentRepository(app_context)

    scheduler.add_job(
        capture_uncaptured_payment_intents,
        "cron",
        minute="*/1",
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
