import asyncio
import os
import signal

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from doordash_python_stats.ddstats import doorstats_global, DoorStatsProxyMultiServer

from app.commons.config.utils import init_app_config
from app.commons.context.app_context import create_app_context
from app.commons.context.logger import get_logger
from app.commons.instrumentation.pool import stat_resource_pool_jobs
from app.commons.jobs.pool import JobPool, adjust_pool_sizes
from app.commons.runtime import runtime
from app.commons.stats import init_global_statsd
from app.payin.jobs import (
    capture_uncaptured_payment_intents,
    resolve_capturing_payment_intents,
)


def scheduler_heartbeat(statsd_client: DoorStatsProxyMultiServer) -> None:
    """
    Sends a heartbeat from the scheduler

    :param statsd_client: client to use to send heartbeat
    :return: None
    """
    statsd_client.incr("scheduler.heartbeat")


app_config = init_app_config()

if app_config.SENTRY_CONFIG:
    sentry_sdk.init(
        dsn=app_config.SENTRY_CONFIG.dsn.value,
        environment=app_config.SENTRY_CONFIG.environment,
        release=app_config.SENTRY_CONFIG.release,
    )

# set up global statsd
init_global_statsd(
    prefix=app_config.GLOBAL_STATSD_PREFIX,
    host=app_config.STATSD_SERVER,
    fixed_tags={"env": app_config.ENVIRONMENT},
)

logger = get_logger("cron")


scheduler = AsyncIOScheduler()
loop = asyncio.get_event_loop()
app_context = loop.run_until_complete(create_app_context(app_config))

stripe_pool = JobPool.create_pool(size=10, name="stripe")
app_context.monitor.add(
    stat_resource_pool_jobs(
        stat_prefix="resource.job_pools",
        pool_name=stripe_pool.name,
        pool_job_stats=stripe_pool,
    )
)


scheduler.add_job(
    capture_uncaptured_payment_intents,
    trigger="cron",
    minute="*/5",
    kwargs={"app_context": app_context, "job_pool": stripe_pool},
)

scheduler.add_job(
    resolve_capturing_payment_intents,
    trigger="cron",
    minute="*/5",
    kwargs={"app_context": app_context, "job_pool": stripe_pool},
)

scheduler.add_job(
    scheduler_heartbeat,
    trigger="cron",
    minute="*/1",
    kwargs={"statsd_client": doorstats_global},
)

scheduler.add_job(
    adjust_pool_sizes, trigger="cron", second="*/30", kwargs={"runtime": runtime}
)

scheduler.start()


async def handle_shutdown():
    logger.info("Received scheduler shutdown request")
    scheduler.shutdown()
    count, _results = await stripe_pool.cancel()
    logger.info("Cancelled stripe pool", count=count)
    loop.stop()
    logger("Done shutting down!")


loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(handle_shutdown()))

print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))

loop.run_forever()
